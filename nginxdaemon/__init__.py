#!/bin/python3
import logging
from logging import handlers, config
from monitor import MonitorDaemon
from pathlib import Path

logger = logging.getLogger(__name__)


BASE_PATH = Path(__file__).resolve().parent
PROJ_PATH = Path(__file__).resolve().parent.parent

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {  # Change the name to avoid conflicts with the built-in handler
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "standard",
            "filename": str(
                BASE_PATH / "logs" / "monitor.log"
            ),  # Using the operator of Path object
            "when": "D",
            "interval": 1,  # Clearly specify the interval, although the default is 1 day
            "backupCount": 3,
            "encoding": "utf-8",
        },
        "error_file": {
            "level": "ERROR",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": str(BASE_PATH / "logs" / "monitor_error.log"),
            "mode": "a",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "file", "error_file"],  # Use a new handler name
            "level": "INFO",
            "propagate": True,
        }
    },
}


if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    nmd = MonitorDaemon(
        nginx_runner_path=f"{PROJ_PATH}/nginx/nginx",
        nginx_context_path=f"{PROJ_PATH}/nginx/",
        nginx_status_url="http://127.0.0.1/status",
    )
    nmd.start()
