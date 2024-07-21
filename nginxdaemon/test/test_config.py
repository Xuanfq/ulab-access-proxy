#!/bin/python3
import logging
from pathlib import Path
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config


BASE_PATH = Path(__file__).resolve().parent.parent
PROJ_PATH = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


def test_config_nginx_daemon_config_get():
    logger.info("======= Testing config.nginx_daemon_config_get")
    success, data = config.nginx_daemon_config_get()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_config_nginx_daemon_config_set():
    logger.info("======= Testing config.nginx_daemon_config_set")
    success, src = config.nginx_daemon_config_get()
    assert success
    src["test"] = "test"
    success, data = config.nginx_daemon_config_set(src)
    assert success
    success, src = config.nginx_daemon_config_get()
    assert success
    assert "test" in src
    del src["test"]
    success, data = config.nginx_daemon_config_set(src)
    assert success
    success, src = config.nginx_daemon_config_get()
    assert success
    assert "test" not in src
    # success, data = config.nginx_daemon_config_set("""[default]
    #                                                abc=def""")
    # assert success
    # success, src = config.nginx_daemon_config_get()
    # assert success
    # assert "abc" in src
    logger.info(f"======= Test result: {True}")


def test_config_nginx_config_get():
    logger.info("======= Testing config.nginx_config_get")
    success, data = config.nginx_config_get()
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_config_nginx_config_set_custom():
    logger.info("======= Testing config.nginx_config_set_custom")
    success, data = config.nginx_config_set_custom(
        cfg_filename="../nginx_test.conf", cfg="xxxx"
    )
    assert success
    logger.info(f"======= Test result: {success}, data:{data}")


def test_config_nginx_config_get_custom():
    logger.info("======= Testing config.nginx_config_get_custom")
    success, data = config.nginx_config_get_custom()
    assert success
    logger.info(f"======= Test result: {success}, data:{data.keys()}, detail:{data}")


def test():
    logger.info("Tests starting...")
    logger.info("Testing config...")
    # test_config_nginx_daemon_config_get()
    # test_config_nginx_daemon_config_set()
    # test_config_nginx_config_get()
    # test_config_nginx_config_set_custom()
    test_config_nginx_config_get_custom()
    logger.info("Tests finished.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s - %(levelname)s]: %(message)s"
    )
    test()
