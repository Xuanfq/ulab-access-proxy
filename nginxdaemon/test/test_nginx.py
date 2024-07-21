#!/bin/python3
import logging
import time
from pathlib import Path
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from nginx import NginxUtils


BASE_PATH = Path(__file__).resolve().parent.parent
PROJ_PATH = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


def test_nginx_utils():
    nu = NginxUtils(
        nginx_runner_path=f"{PROJ_PATH}/nginx/nginx",
        nginx_context_path=f"{PROJ_PATH}/nginx/",
    )
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


def test():
    logger.info("Tests starting...")
    logger.info("Testing NginxUtils...")
    test_nginx_utils()
    logger.info("Tests finished.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s - %(levelname)s]: %(message)s"
    )
    test()
