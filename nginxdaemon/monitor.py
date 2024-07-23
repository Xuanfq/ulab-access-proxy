#!/bin/python3
import time
import logging
import os
from threading import Thread
from pathlib import Path
import signal
import argparse
from nginx import NginxUtils
from nacos import NacosClient
import config


BASE_PATH = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)


class MonitorDaemon:
    def __init__(
        self,
        nginx_runner_path: str,
        nginx_context_path: str,
        nginx_status_url: str = "http://127.0.0.1/status",
    ):
        """Monitor daemon for nginx

        Args:
            nginx_runner_path (str): nginx runner path (bin file)
            nginx_context_path (str): nginx context path (conf dir, equal to nginx -p $nginx_context_path)
            nginx_status_url (_type_, optional): the access path for stub_status of nginx. Defaults to "http://127.0.0.1/status".
        """
        self.daemon = False
        self.running = False
        self.command_file = f"{BASE_PATH}/logs/cmd"
        self.check_alive_interval = 5
        self.check_command_interval = 1
        self.check_config_interval = 30
        self.nginx_runner_path = nginx_runner_path  # fixed value from function
        self.nginx_context_path = nginx_context_path  # fixed value from function
        self.nginx_status_url = nginx_status_url
        self.nginx: NginxUtils = None
        self.nacos_address = None
        self.nacos_port = None
        self.nacos_username = None
        self.nacos_password = None
        self.nacos: NacosClient = None
        self.config_dict = {}
        self.nginx_status_monitoring_thread: Thread = None
        self.command_input_monitoring_thread: Thread = None
        self.config_status_monitoring_thread: Thread = None
        # load config
        self._load_config()
        self._load_daemon()

    def _load_config(self):
        success, data = config.nginx_daemon_config_get()
        if success:
            if "check_alive_interval" in data:
                self.check_alive_interval = int(data["check_alive_interval"])
            if "check_command_interval" in data:
                self.check_command_interval = int(data["check_command_interval"])
            if "check_config_interval" in data:
                self.check_config_interval = int(data["check_config_interval"])
            if "nginx_status_url" in data:
                self.nginx_status_url = data["nginx_status_url"]
            if self.nginx is not None:
                self.nginx.nginx_status_url = self.nginx_status_url
            if "nacos_address" in data:
                self.nacos_address = data["nacos_address"]
            if "nacos_port" in data:
                self.nacos_port = data["nacos_port"]
            if "nacos_username" in data:
                self.nacos_username = data["nacos_username"]
            if "nacos_password" in data:
                self.nacos_password = data["nacos_password"]
            self.config_dict = data
        logger.info(f"Load config: {self.config_dict}")

    def _load_daemon(self):
        # init nginx tool
        self.nginx = NginxUtils(
            self.nginx_runner_path, self.nginx_context_path, self.nginx_status_url
        )
        # init nacos client
        if self.nacos_address and self.nacos_port:
            self.nacos = NacosClient(
                self.nacos_address,
                self.nacos_port,
                self.nacos_username,
                self.nacos_password,
            )
        # add signal handler
        signal.signal(signal.SIGTERM, self._handle_signal)  # kill
        signal.signal(signal.SIGINT, self._handle_signal)  # ctrl+c
        # start the command daemon
        self.daemon = True
        self.command_input_monitoring_thread = Thread(target=self.command_input_monitor)
        self.command_input_monitoring_thread.start()
        logger.info("Command input monitor daemon started...")

    def _handle_signal(self, signum, frame):
        if signum == signal.SIGINT:
            # ctrl + c
            if not self.running:
                # ctrl + c again to exit (2 times)
                self.quit()
            else:
                # ctrl + c to stop (1 time)
                self.stop()
        elif signum == signal.SIGTERM:
            # kill
            self.quit()
        else:
            self.stop()

    def start(self):
        """
        start the monitors
        """
        logger.info("Starting monitor...")
        self.running = True
        self.nginx_status_monitoring_thread = Thread(target=self.nginx_status_monitor)
        self.nginx_status_monitoring_thread.start()
        logger.info("Nginx status monitor started...")
        self.config_status_monitoring_thread = Thread(target=self.config_status_monitor)
        self.config_status_monitoring_thread.start()
        logger.info("Config status monitor started...")

    def stop(self):
        """
        stop the monitors
        """
        logger.info("Stopping monitors...")
        self.running = False

    def quit(self):
        """
        stop the nginx monitor and monitor command daemon
        """
        logger.info("Quiting nginx monitor and command daemon...")
        self.running = False
        self.daemon = False

    def nginx_status_monitor(self):
        while self.running:
            self.nginx.status()
            if not self.nginx.nginx_alive:
                logger.error(f"Nginx is not alive, restarting...")
                self.nginx.restart()
            else:
                logger.info("Nginx is alive...")
            time.sleep(self.check_alive_interval)
        logger.info("Nginx monitor stopped...")

    def config_status_monitor(self):
        """sync config from nacos"""
        while self.running:
            self._load_config()
            try:
                skip_sync = False
                if self.nacos is None:
                    logger.debug("Nacos is not initialized, skip sync config")
                    skip_sync = True
                if not skip_sync and (
                    not self.nacos.alive()
                    and not self.nacos.login()[0]
                    and self.nacos.alive()
                ):
                    logger.debug("Nacos is not alive, skip sync config")
                    skip_sync = True
                if not skip_sync:
                    namespace = self.config_dict["nacos_namespace"]
                    group = self.config_dict["nacos_group"]
                    conf_series_data_id = self.config_dict["nacos_conf_series_data_id"]
                    conf_version_data_id = self.config_dict[
                        "nacos_conf_version_data_id"
                    ]
                    auto_reload_nginx = bool(
                        self.config_dict["nacos_auto_reload_nginx"]
                    )
                    conf_version_success, local_conf_version = (
                        config.nginx_config_get_custom(conf_version_data_id)
                    )
                    if conf_version_success:
                        local_conf_version = int(str(local_conf_version).strip())
                    else:
                        raise Exception("Get config version from local error")
                    nacos_conf_version_success, nacos_conf_version = (
                        self.nacos.config_get(conf_version_data_id, group, namespace)
                    )
                    if nacos_conf_version_success:
                        nacos_conf_version = int(str(nacos_conf_version).strip())
                        if nacos_conf_version == local_conf_version:
                            logger.info("Nginx config is up to date")
                            skip_sync = True
                        upload = nacos_conf_version < local_conf_version
                    else:
                        upload = True
                    if not skip_sync:
                        if upload:
                            logger.info(
                                "Local config is newer than nacos, upload to nacos"
                            )
                            success, conf_series = config.nginx_config_get_custom(
                                conf_series_data_id
                            )
                            logger.debug(f"Get config series from local:{conf_series}")
                            if not success:
                                raise Exception(
                                    f"Get config series from local error: {conf_series}"
                                )
                            for config_name in conf_series.split("\n"):
                                config_name = config_name.strip()
                                success, content = config.nginx_config_get_custom(
                                    config_name
                                )
                                if not success:
                                    raise Exception(
                                        f"Get config {config_name} from local error: {content}"
                                    )
                                logger.debug(
                                    f"Upload config {config_name} to nacos:{content}"
                                )
                                success, result = self.nacos.config_publish(
                                    data_id=config_name,
                                    group=group,
                                    content=content,
                                    tenant=namespace,
                                )
                                if success and result:
                                    logger.info(
                                        f"Upload config {config_name} to nacos[{namespace}/{group}/{config_name}] success"
                                    )
                                else:
                                    logger.error(
                                        f"Upload config {config_name} to nacos error"
                                    )
                            logger.info("Upload config to nacos success")
                        else:
                            logger.info(
                                "Local config is older than nacos, download from nacos"
                            )
                            success, conf_series = self.nacos.config_get(
                                data_id=conf_series_data_id,
                                group=group,
                                tenant=namespace,
                            )
                            if not success:
                                raise Exception("Get config series from nacos error")
                            for config_name in conf_series.split("\n"):
                                config_name = config_name.strip()
                                success, content = self.nacos.config_get(
                                    data_id=config_name, group=group, tenant=namespace
                                )
                                result, msg = config.nginx_config_set_custom(
                                    config_name, content
                                )
                                if success and result:
                                    logger.info(
                                        f"Download config {config_name} to local success"
                                    )
                                else:
                                    logger.error(
                                        f"Download config {config_name} to local error"
                                    )
                            if auto_reload_nginx:
                                logger.info("Reloading nginx...")
                                if self.nginx.test_config():
                                    logger.info("Nginx config test success")
                                    self.nginx.reload()
                            logger.info("Download config from nacos success")
            except Exception as e:
                logger.error(f"Sync config from nacos error: {e}")
            time.sleep(self.check_config_interval)
        logger.info("Config monitor stopped...")

    def command_input_monitor(self):
        parser = argparse.ArgumentParser("")
        parser.add_argument(
            "-n",
            dest="nginx",
            type=str,
            choices=["start", "stop", "restart", "reload", "reopen", "quit"],
            help="nginx command",
        )
        parser.add_argument(
            "-m",
            dest="monitor",
            type=str,
            choices=["start", "stop", "quit"],
            help="monitor command",
        )
        if os.path.exists(self.command_file):
            # remove the existed file
            os.remove(self.command_file)
        while self.daemon:
            logger.debug("Checking command: %s", self.command_file)
            if os.path.exists(self.command_file):
                try:
                    with open(self.command_file, "r") as f:
                        # only one line cmd is available
                        command = f.readline().strip()
                        f.close()
                        logger.info(f"Received command: '{command}'")
                        args = parser.parse_args(
                            [item for item in command.split(" ") if item.strip() != ""]
                        )
                        if args.nginx == "start":
                            self.nginx.start()
                        elif args.nginx == "restart":
                            self.nginx.restart()
                        elif args.nginx == "reload":
                            self.nginx.reload()
                        elif args.nginx == "reopen":
                            self.nginx.reopen()
                        elif args.nginx == "stop":
                            self.nginx.stop()
                        elif args.nginx == "quit":
                            self.nginx.quit()
                        if args.monitor == "start":
                            self.start()
                        elif args.monitor == "stop":
                            self.stop()
                        elif args.monitor == "quit":
                            self.quit()
                except SystemExit as e:
                    logger.error(
                        f"Error while parsing command, unrecognized arguments: {command}"
                    )
                except Exception as e:
                    logger.error(f"Error while parsing command: {e}")
                try:
                    os.remove(self.command_file)  # remove file
                except Exception as e:
                    pass
            time.sleep(self.check_command_interval)
        logger.info("Nginx monitor command daemon stopped...")
