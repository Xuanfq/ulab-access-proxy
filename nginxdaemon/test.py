#!/bin/python3
import logging
from server import NginxUtils, NginxMonitorDaemon
import time
from pathlib import Path


BASE_PATH = Path(__file__).resolve().parent
PROJ_PATH = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s - %(levelname)s]: %(message)s"
)
logger = logging.getLogger(__name__)


def test_nginx_utils(**kwargs):
    nu = NginxUtils(**kwargs)
    nu.alive()
    nu.test_config()
    nu.start()
    time.sleep(5)  # Wait for Nginx to start
    nu.reload()
    nu.reopen()
    time.sleep(5)  # Wait for operations to complete
    nu.restart()
    nu.version()
    nu.info()
    nu.status()
    time.sleep(5)
    print(nu.status())
    time.sleep(2)
    nu.quit()
    nu.stop()
    nu.start()


def test_nginx_daemon(**kwargs):
    nmd = NginxMonitorDaemon(**kwargs)
    nmd.start()


if __name__ == "__main__":
    logger.info("Starting tests...")
    logger.info("testing NginxUtils...")
    test_nginx_utils(
        nginx_runner_path=f"{PROJ_PATH}/nginx/nginx",
        nginx_context_path=f"{PROJ_PATH}/nginx/",
    )
    time.sleep(5)
    logger.info("testing NginxDaemon...")
    test_nginx_daemon(
        nginx_runner_path=f"{PROJ_PATH}/nginx/nginx",
        nginx_context_path=f"{PROJ_PATH}/nginx/",
    )
    pass
