"""Tests for logging configuration — NVR debug levels."""

import logging

import pytest

from remander.logging import TruncateFilter, setup_logging


@pytest.fixture(autouse=True)
def _reset_loggers():
    """Reset reolink_aio logger levels and filters after each test."""
    yield
    for name in ("reolink_aio", "reolink_aio.api", "reolink_aio.baichuan"):
        lgr = logging.getLogger(name)
        lgr.setLevel(logging.NOTSET)
        lgr.filters.clear()


class TestNvrDebugLevels:
    """NVR_DEBUG supports three levels: false, true, full."""

    def test_nvr_debug_false_sets_all_to_warning(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="false")

        assert logging.getLogger("reolink_aio").level == logging.WARNING
        assert logging.getLogger("reolink_aio.api").level == logging.NOTSET
        assert logging.getLogger("reolink_aio.baichuan").level == logging.NOTSET

    def test_nvr_debug_true_enables_api_only(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="true")

        assert logging.getLogger("reolink_aio.api").level == logging.DEBUG
        # Parent stays at WARNING so baichuan inherits WARNING
        assert logging.getLogger("reolink_aio").level == logging.WARNING
        assert logging.getLogger("reolink_aio.baichuan").level == logging.NOTSET

    def test_nvr_debug_full_enables_everything(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="full")

        assert logging.getLogger("reolink_aio").level == logging.DEBUG

    def test_nvr_debug_default_is_false(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path))

        assert logging.getLogger("reolink_aio").level == logging.WARNING


class TestTruncateFilter:
    """Log messages exceeding max_length are truncated."""

    def test_short_message_passes_through(self):
        f = TruncateFilter(max_length=100)
        record = logging.LogRecord("test", logging.DEBUG, "", 0, "short msg", (), None)
        f.filter(record)
        assert record.getMessage() == "short msg"

    def test_long_message_is_truncated(self):
        f = TruncateFilter(max_length=50)
        long_msg = "x" * 200
        record = logging.LogRecord("test", logging.DEBUG, "", 0, long_msg, (), None)
        f.filter(record)
        result = record.getMessage()
        assert len(result) < 200
        assert result.endswith("... (truncated, 200 chars total)")

    def test_long_message_with_args_is_truncated(self):
        f = TruncateFilter(max_length=50)
        payload = "y" * 200
        record = logging.LogRecord(
            "test", logging.DEBUG, "", 0, "Response: %s", (payload,), None
        )
        f.filter(record)
        result = record.getMessage()
        assert len(result) < 250
        assert "truncated" in result

    def test_filter_always_returns_true(self):
        f = TruncateFilter(max_length=10)
        record = logging.LogRecord("test", logging.DEBUG, "", 0, "x" * 100, (), None)
        assert f.filter(record) is True


class TestTruncateFilterIntegration:
    """Truncate filter is attached when NVR_DEBUG is true or full."""

    def _has_truncate_filter(self, logger_name: str) -> bool:
        return any(
            isinstance(f, TruncateFilter) for f in logging.getLogger(logger_name).filters
        )

    def test_nvr_debug_false_no_filter(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="false")
        assert not self._has_truncate_filter("reolink_aio")
        assert not self._has_truncate_filter("reolink_aio.api")

    def test_nvr_debug_true_has_filter_on_api(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="true")
        assert self._has_truncate_filter("reolink_aio.api")

    def test_nvr_debug_full_has_filter_on_parent(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="full")
        assert self._has_truncate_filter("reolink_aio")
