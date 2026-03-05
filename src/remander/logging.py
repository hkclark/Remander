"""Logging configuration — dual output to stdout and rotating file."""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

DEFAULT_NVR_LOG_MAX_LENGTH = 0


class TruncateFilter(logging.Filter):
    """Truncates log messages from a logger hierarchy that exceed max_length.

    Uses logging.Filter's built-in name filtering: passing name="reolink_aio"
    means this filter only applies to records from reolink_aio and its children.
    Attach to handlers (not loggers) so propagated child records are caught.
    """

    def __init__(
        self, name: str = "", max_length: int = DEFAULT_NVR_LOG_MAX_LENGTH
    ) -> None:
        super().__init__(name)
        self.max_length = max_length

    def filter(self, record: logging.LogRecord) -> bool:
        if not super().filter(record):
            return True  # not our logger hierarchy — pass through unmodified
        full_message = record.getMessage()
        if len(full_message) > self.max_length:
            record.msg = f"{full_message[:self.max_length]}... (truncated, {len(full_message)} chars total)"
            record.args = None
        return True


def setup_logging(
    log_dir: str = "./logs",
    log_level: str = "INFO",
    *,
    nvr_debug: str = "false",
    nvr_debug_max_length: int = DEFAULT_NVR_LOG_MAX_LENGTH,
) -> None:
    """Configure application logging with stdout and file handlers.

    Args:
        log_dir: Directory for log files.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        nvr_debug: NVR debug level — "false" (warnings only), "true" (HTTP API debug),
            or "full" (all reolink-aio debug including Baichuan protocol).
        nvr_debug_max_length: Max character length for reolink-aio debug messages.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
    formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear any existing handlers (avoid duplicates on reload)
    root_logger.handlers.clear()

    # Stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Rotating file handler (weekly rotation, keep 8 weeks)
    file_handler = TimedRotatingFileHandler(
        filename=log_path / "remander.log",
        when="W0",  # Rotate on Monday
        backupCount=8,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(file_handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("tortoise").setLevel(logging.WARNING)

    # NVR debug logging — reolink-aio has 200+ DEBUG statements covering
    # HTTP requests/responses, connection state, and Baichuan protocol traffic.
    # "true" enables only the HTTP API logger (and children like .api.data);
    # "full" enables everything including Baichuan protocol.
    # The truncate filter is on the handlers so it catches records from child
    # loggers (e.g. reolink_aio.api.data) that propagate up without passing
    # through parent logger filters.
    nvr_debug_level = nvr_debug.lower()
    if nvr_debug_level == "full":
        logging.getLogger("reolink_aio").setLevel(logging.DEBUG)
        if nvr_debug_max_length > 0:
            truncate = TruncateFilter(name="reolink_aio", max_length=nvr_debug_max_length)
            stdout_handler.addFilter(truncate)
            file_handler.addFilter(truncate)
    elif nvr_debug_level == "true":
        logging.getLogger("reolink_aio").setLevel(logging.WARNING)
        logging.getLogger("reolink_aio.api").setLevel(logging.DEBUG)
        if nvr_debug_max_length > 0:
            truncate = TruncateFilter(name="reolink_aio.api", max_length=nvr_debug_max_length)
            stdout_handler.addFilter(truncate)
            file_handler.addFilter(truncate)
    else:
        logging.getLogger("reolink_aio").setLevel(logging.WARNING)
