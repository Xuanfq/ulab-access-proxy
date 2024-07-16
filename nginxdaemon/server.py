#!/bin/python3
import time
import subprocess
import logging
import os
import re
from threading import Thread
from pathlib import Path
import signal
import argparse


BASE_PATH = Path(__file__).resolve().parent

logger = logging.getLogger(__name__)


class NginxUtils:
    def __init__(
        self,
        nginx_runner_path,
        nginx_context_path,
        nginx_status_url: str = "http://localhost/status",
    ):
        """_summary_

        Args:
            nginx_runner_path (str): nginx runner path (bin file)
            nginx_context_path (str): nginx context path (conf dir, equal to nginx -p $nginx_context_path)
            nginx_status_url (_type_, optional): the access path for stub_status of nginx. Defaults to "http://127.0.0.1/status".
        """
        self.nginx = nginx_runner_path
        self.nginx_context_path = nginx_context_path
        self.nginx_cmd = f"{self.nginx} -p {self.nginx_context_path} "
        self.nginx_alive = False
        self.nginx_status = {}
        self.nginx_version = "unknown"
        self.nginx_info = ""
        self.nginx_active_connections = -1
        self.nginx_server_accepts = -1
        self.nginx_server_handled = -1
        self.nginx_server_requests = -1
        self.nginx_reading = -1
        self.nginx_writing = -1
        self.nginx_waiting = -1
        self.nginx_status_url = nginx_status_url

    def _run_command(self, command):
        """Run an Nginx command and return the output."""
        try:
            status, output = subprocess.getstatusoutput(command)
            logger.debug(f"==== command ==== {command}")
            logger.debug(f"==== result  ==== {status == 0} {output}")
            return status == 0, output
        except Exception as e:
            return False, str(e)

    def start(self):
        """Start the Nginx service."""
        success, output = self._run_command(f"{self.nginx_cmd}")
        if success:
            logger.info("Nginx started successfully.")
        else:
            logger.error(f"Failed to start Nginx: {output}")
        return success

    def stop(self):
        """Stop the Nginx service."""
        success, output = self._run_command(f"{self.nginx_cmd} -s stop")
        if success:
            logger.info("Nginx stopped successfully.")
        else:
            logger.error(f"Failed to stop Nginx: {output}")
        return success

    def quit(self):
        """
        Quit the Nginx service gracefully.
        This will wait for all connections to close,
        so it will ensure that all buffer data is sent,
        all logs are written, and all resources are properly released.
        """
        success, output = self._run_command(f"{self.nginx_cmd} -s quit")
        if success:
            logger.info("Nginx quit successfully.")
        else:
            logger.error(f"Failed to quit Nginx: {output}")
        return success

    def restart(self):
        """Restart the Nginx service."""
        logger.info("Restarting Nginx...")
        s1 = self.stop()
        time.sleep(3)  # Wait for Nginx to fully stop
        s2 = self.start()
        return s2

    def reload(self):
        """Reload the Nginx configuration."""
        success, output = self._run_command(f"{self.nginx_cmd} -s reload")
        if success:
            logger.info("Nginx configuration reloaded successfully.")
        else:
            logger.error(f"Failed to reload Nginx configuration: {output}")
        return success

    def test_config(self):
        """Test the Nginx configuration."""
        success, output = self._run_command(f"{self.nginx_cmd} -t")
        if "successful" in output:
            logger.info("Nginx configuration test passed.")
            return True
        else:
            logger.error(f"Nginx configuration test failed: {output}")
        return False

    def reopen(self):
        """Reopen the Nginx logs."""
        success, output = self._run_command(f"{self.nginx_cmd} -s reopen")
        if success:
            logger.info("Nginx logs reopened successfully.")
        else:
            logger.error(f"Failed to reopen Nginx logs: {output}")
        return success

    def version(self):
        """Get the Nginx version."""
        success, output = self._run_command(f"{self.nginx_cmd} -v")
        if success:
            self.nginx_version = output.split()[2]
            logger.info(f"Nginx version: {self.nginx_version}")
        else:
            logger.error(f"Failed to get Nginx version: {output}")
        return success, self.nginx_version

    def info(self):
        """Get the Nginx info."""
        success, output = self._run_command(f"{self.nginx_cmd} -V")
        if success:
            self.nginx_info = output
            logger.info(f"Nginx info: {self.nginx_info}")
        else:
            logger.error(f"Failed to get Nginx info: {output}")
        return success, self.nginx_info

    def alive(self):
        """Check if Nginx is alive."""
        success, output = self._run_command(f"curl {self.nginx_status_url}")
        if success:
            if output.count("Active") > 0:
                self.nginx_alive = True
                logger.info(f"Success to check Nginx alive or not: alive")
            else:
                self.nginx_alive = False
                logger.error(f"Failed to check Nginx alive or not: {output}")
        else:
            self.nginx_alive = False
            logger.error(f"Failed to check Nginx alive or not: {output}")
        return self.nginx_alive

    def status(self):
        """Get the Nginx status."""
        success, output = self._run_command(f"curl {self.nginx_status_url}")
        if success:
            pattern = r"Active connections: (\d+)\s*.*\s*server accepts handled requests\s*(\d+)\s*(\d+)\s*(\d+)\s*Reading: (\d+)\s*Writing: (\d+)\s*Waiting: (\d+)"
            match = re.search(pattern, output)
            if match:
                active_connections = int(match.group(1))
                server_accepts = int(match.group(2))
                server_handled = int(match.group(3))
                server_requests = int(match.group(4))
                reading = int(match.group(5))
                writing = int(match.group(6))
                waiting = int(match.group(7))

                self.nginx_alive = True
                self.nginx_active_connections = active_connections
                self.nginx_server_accepts = server_accepts
                self.nginx_server_handled = server_handled
                self.nginx_server_requests = server_requests
                self.nginx_reading = reading
                self.nginx_writing = writing
                self.nginx_waiting = waiting

                logger.info(f"Alive: {self.nginx_alive}")
                logger.info(f"Active connections: {active_connections}")
                logger.info(f"Server accepts: {server_accepts}")
                logger.info(f"Server handled: {server_handled}")
                logger.info(f"Server requests: {server_requests}")
                logger.info(f"Reading: {reading}")
                logger.info(f"Writing: {writing}")
                logger.info(f"Waiting: {waiting}")
            else:
                self.nginx_alive = self.alive()
                self.nginx_active_connections = -1
                self.nginx_server_accepts = -1
                self.nginx_server_handled = -1
                self.nginx_server_requests = -1
                self.nginx_reading = -1
                self.nginx_writing = -1
                self.nginx_waiting = -1

                success = False
                logger.error(f"Failed to parse Nginx status: {output}")
        else:
            logger.error(f"Failed to get Nginx status: {output}")
            self.nginx_alive = False
            self.nginx_active_connections = -1
            self.nginx_server_accepts = -1
            self.nginx_server_handled = -1
            self.nginx_server_requests = -1
            self.nginx_reading = -1
            self.nginx_writing = -1
            self.nginx_waiting = -1
        self.nginx_status = {
            "alive": self.nginx_alive,
            "active_connections": self.nginx_active_connections,
            "server_accepts": self.nginx_server_accepts,
            "server_handled": self.nginx_server_handled,
            "server_requests": self.nginx_server_requests,
            "reading": self.nginx_reading,
            "writing": self.nginx_writing,
            "waiting": self.nginx_waiting,
        }
        return success, self.nginx_status


class NginxMonitorDaemon:
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
        # init nginx tool
        self.nginx = NginxUtils(nginx_runner_path, nginx_context_path, nginx_status_url)
        # add signal handler
        signal.signal(signal.SIGTERM, self._handle_signal)  # kill
        signal.signal(signal.SIGINT, self._handle_signal)  # ctrl+c
        # start the daemon
        self.daemon = True
        self.check_command_thread = Thread(target=self.check_command)
        self.check_command_thread.start()
        logger.info("Nginx monitor command daemon started...")

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
        self.check_alive_thread = Thread(target=self.check_alive)
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

    def check_alive(self):
        while self.running:
            self.nginx.status()
            if not self.nginx.nginx_alive:
                logger.error(f"Nginx is not alive, restarting...")
                self.nginx.restart()
            else:
                logger.info("Nginx is alive...")
            time.sleep(self.check_alive_interval)
        logger.info("Nginx monitor stopped...")

    def check_command(self):
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
                    logger.error(f"Error while parsing command, unrecognized arguments: {command}")
                except Exception as e:
                    logger.error(f"Error while parsing command: {e}")
                try:
                    os.remove(self.command_file)  # remove file
                except Exception as e:
                    pass
            time.sleep(self.check_command_interval)
        logger.info("Nginx monitor command daemon stopped...")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="[%(asctime)s - %(levelname)s]: %(message)s"
    )
    pass
