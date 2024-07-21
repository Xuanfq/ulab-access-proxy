#!/bin/python3
import time
import subprocess
import logging
import re


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
