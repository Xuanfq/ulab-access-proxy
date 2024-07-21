#!/bin/python3
import logging
from pathlib import Path
import configparser
import os

BASE_PATH = Path(__file__).resolve().parent
PROJ_PATH = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

CONFIG_BASE_PATH = PROJ_PATH / "conf"
NGINX_CONFIG_FILE = CONFIG_BASE_PATH / "nginx.conf"
NGINX_DAEMON_CONFIG_FILE = CONFIG_BASE_PATH / "nginxdaemon.ini"


def nginx_daemon_config_get():
    try:
        config = configparser.ConfigParser()
        config.read(NGINX_DAEMON_CONFIG_FILE, encoding="utf-8")
        if "default" not in config.sections():
            msg = "default section not found in nginxdaemon.ini"
            logger.error(msg)
            return False, msg
        else:
            cfg_dict = dict(config["default"])
            if "override" in config.sections():
                cfg_dict.update(dict(config["override"]))
            return True, cfg_dict
    except Exception as e:
        msg = f"Error getting nginx daemon config: {e}"
        logger.error(msg)
        return False, msg


def nginx_daemon_config_set(cfg: str | dict):
    try:
        # str
        if type(cfg) == str:
            with open(NGINX_DAEMON_CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(cfg)
            return True, None
        # dict
        config = configparser.ConfigParser()
        config.read(NGINX_DAEMON_CONFIG_FILE, encoding="utf-8")
        config["override"] = cfg
        with open(NGINX_DAEMON_CONFIG_FILE, "w", encoding="utf-8") as f:
            config.write(f)
        return True, None
    except Exception as e:
        msg = f"Error setting nginx daemon config: {e}"
        logger.error(msg)
        return False, msg


def nginx_config_get():
    try:
        with open(NGINX_CONFIG_FILE, "r", encoding="utf-8") as f:
            return True, f.read()
    except Exception as e:
        msg = f"Error getting nginx config: {e}"
        logger.error(msg)
        return False, msg


def nginx_config_set(cfg: str):
    try:
        with open(NGINX_CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(cfg)
        return True, None
    except Exception as e:
        msg = f"Error getting nginx config: {e}"
        logger.error(msg)
        return False, msg


def nginx_config_set_custom(cfg_filename: str, cfg: str):
    try:
        filepath = (CONFIG_BASE_PATH / cfg_filename).parent
        if cfg_filename.count("/") > 0 or not filepath.is_relative_to(CONFIG_BASE_PATH):
            msg = "Invalid path"
            logger.error(msg)
            return False, msg
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cfg)
        return True, None
    except Exception as e:
        msg = f"Error setting custom config: {e}"
        logger.error(msg)
        return False, msg


def nginx_config_get_custom(cfg_filename: str = None):
    """_summary_

    Args:
        cfg_filename (str, optional): config filename. Defaults to None.

    Returns:
        (dict[filename,content] | str): return dict if cfg_filename is None, otherwise return str (config content)
    """
    try:
        if cfg_filename is not None:
            filepath = (CONFIG_BASE_PATH / cfg_filename).parent
            if cfg_filename.count("/") > 0 or not filepath.is_relative_to(
                CONFIG_BASE_PATH
            ):
                msg = "Invalid path"
                logger.error(msg)
                return False, msg
        cfg_dict = {}
        for cfg_file in os.listdir(CONFIG_BASE_PATH):
            # only allow same level files, not allow subdirectories
            filepath = CONFIG_BASE_PATH / cfg_file
            if cfg_filename is not None and cfg_filename == cfg_file:
                if os.path.isfile(filepath):
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        return True, f.read()
                msg = "Config file not found"
                logger.error(msg)
                return False, msg
            elif os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    cfg_dict[cfg_file] = f.read()
        return True, cfg_dict
    except Exception as e:
        msg = f"Error setting custom config: {e}"
        logger.error(msg)
        return False, msg
