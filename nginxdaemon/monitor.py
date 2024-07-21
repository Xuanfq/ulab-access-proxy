#!/bin/python3
import time
import logging
import os
from threading import Thread
from pathlib import Path
import signal
import argparse
from nginx import NginxUtils
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
        """_summary_

        Args:
            nginx_runner_path (str): nginx runner path (bin file)
            nginx_context_path (str): nginx context path (conf dir, equal to nginx -p $nginx_context_path)
            nginx_status_url (_type_, optional): the access path for stub_status of nginx. Defaults to "http://127.0.0.1/status".
        """
        self.daemon = False
        self.running = False
        self.command_file = f"{BASE_PATH}/logs/cmd"
        self.check_alive_interval = 5
        self.check_alive_thread = None
        self.check_command_interval = 1
        self.check_command_thread = None
        self.nginx_status_url = nginx_status_url
        self.nginx = None
        self.config_dict = {}
        # load config
        self._load_config()
        # init nginx tool
        self.nginx = NginxUtils(
            nginx_runner_path, nginx_context_path, self.nginx_status_url
        )
        # add signal handler
        signal.signal(signal.SIGTERM, self._handle_signal)  # kill
        signal.signal(signal.SIGINT, self._handle_signal)  # ctrl+c
        # start the daemon
        self.daemon = True
        self.check_command_thread = Thread(target=self.daemon_cmd_monitor)
        self.check_command_thread.start()
        logger.info("Nginx monitor command daemon started...")

    def _load_config(self):
        success, data = config.nginx_daemon_config_get()
        if success:
            self.check_alive_interval = int(data["check_alive_interval"])
            self.check_command_interval = int(data["check_command_interval"])
            self.nginx_status_url = data["nginx_status_url"]
            if self.nginx is not None:
                self.nginx.nginx_status_url = self.nginx_status_url
            self.config_dict = data
        logger.info(f"Load config: {self.config_dict}")

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
        start the nginx monitor
        """
        logger.info("Starting nginx monitor...")
        self.running = True
        self.check_alive_thread = Thread(target=self.nginx_status_monitor)
        self.check_alive_thread.start()
        logger.info("Nginx monitor started...")

    def stop(self):
        """
        stop the nginx monitor
        """
        logger.info("Stopping nginx monitor...")
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

    def daemon_cmd_monitor(self):
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
