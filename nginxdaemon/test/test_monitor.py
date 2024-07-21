#!/bin/python3
import logging
from pathlib import Path
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from monitor import MonitorDaemon


BASE_PATH = Path(__file__).resolve().parent.parent
PROJ_PATH = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


def test_nginx_monitor_daemon():
    nmd = MonitorDaemon(
        nginx_runner_path=f"{PROJ_PATH}/nginx/nginx",
        nginx_context_path=f"{PROJ_PATH}/nginx/",
    )
    nmd.start()


def test():
    logger.info("Tests starting...")
    logger.info("Testing NginxDaemon...")
    test_nginx_monitor_daemon()
    logger.info("Tests finished.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s - %(levelname)s]: %(message)s"
    )
    test()
