import logging
import os

_CONFIGURED = False


def setup_logging(level: str = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    raw_level = (level or os.getenv("BITDEV_LOG_LEVEL", "INFO")).upper()
    resolved_level = getattr(logging, raw_level, logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
