"""Structured JSON logging (structlog), safe defaults for production."""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)

    # Even with DEBUG on, these libraries print several lines PER REQUEST (cache lookups,
    # connection pools...) and a Windows console is slow at that. Keep only warnings.
    for noisy in ("cachecontrol", "urllib3", "google", "grpc", "httpcore", "httpx", "asyncio", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer() if debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )