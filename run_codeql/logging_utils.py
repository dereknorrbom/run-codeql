"""Logging setup for run_codeql CLI output."""

import logging
import sys

LOGGER = logging.getLogger("codeql-local")
LOGGER.addHandler(logging.NullHandler())
LOGGER.propagate = False


def configure_logging(quiet: bool) -> None:
    """Configure CLI logging with timestamped stderr output."""
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[codeql-local %(asctime)s] %(message)s", "%H:%M:%S"))
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.ERROR if quiet else logging.INFO)


def err(msg: str) -> None:
    """Log an error with the CLI prefix convention."""
    LOGGER.error("[error] %s", msg)


def log(msg: str) -> None:
    """Log an informational CLI message."""
    LOGGER.info(msg)
