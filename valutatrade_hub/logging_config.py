from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> None:
    settings = SettingsLoader()
    log_file = settings.resolve_path("LOG_FILE")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade.actions")
    if logger.handlers:
        return

    level_name = str(settings.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = RotatingFileHandler(
        log_file,
        maxBytes=int(settings.get("LOG_MAX_BYTES", 1_048_576)),
        backupCount=int(settings.get("LOG_BACKUP_COUNT", 3)),
        encoding="utf-8",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False


def setup_parser_logging() -> logging.Logger:
    settings = SettingsLoader()
    log_file = settings.resolve_path("PARSER_LOG_FILE")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade.parser")
    if logger.handlers:
        return logger

    level_name = str(settings.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = RotatingFileHandler(
        log_file,
        maxBytes=int(settings.get("LOG_MAX_BYTES", 1_048_576)),
        backupCount=int(settings.get("LOG_BACKUP_COUNT", 3)),
        encoding="utf-8",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger
