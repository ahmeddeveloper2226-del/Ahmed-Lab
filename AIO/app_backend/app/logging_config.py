import logging
import sys

from .config import settings


def configure_logging() -> None:
    """
    Called once, at app startup (see main.py). Without this, Python's
    default logging is unconfigured — messages may not appear consistently,
    have no timestamps, and can't be filtered by severity.

    In production (ENVIRONMENT=production), level is INFO — warnings/errors
    only, no verbose debug noise. In development, DEBUG — see everything
    while building.
    """
    log_level = logging.DEBUG if settings.environment != "production" else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()  # avoid duplicate log lines if this runs more than once
    root_logger.addHandler(handler)

    # Quiet down noisy third-party libraries so real app logs aren't buried.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)

    logging.getLogger("wasla.startup").info(
        f"Logging configured — level={logging.getLevelName(log_level)}, environment={settings.environment}"
    )