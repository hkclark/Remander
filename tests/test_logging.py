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

    def test_name_filter_skips_non_matching_records(self):
        f = TruncateFilter(name="reolink_aio.api", max_length=10)
        record = logging.LogRecord("other.logger", logging.DEBUG, "", 0, "x" * 100, (), None)
        f.filter(record)
        # Message should NOT be truncated — wrong logger hierarchy
        assert record.getMessage() == "x" * 100

    def test_name_filter_truncates_matching_records(self):
        f = TruncateFilter(name="reolink_aio.api", max_length=50)
        record = logging.LogRecord(
            "reolink_aio.api.data", logging.DEBUG, "", 0, "x" * 200, (), None
        )
        f.filter(record)
        assert "truncated" in record.getMessage()

    def test_name_filter_truncates_exact_match(self):
        f = TruncateFilter(name="reolink_aio.api", max_length=50)
        record = logging.LogRecord(
            "reolink_aio.api", logging.DEBUG, "", 0, "x" * 200, (), None
        )
        f.filter(record)
        assert "truncated" in record.getMessage()


class TestTruncateFilterIntegration:
    """Truncate filter is on handlers when NVR_DEBUG is true or full."""

    def _get_root_handlers(self) -> list[logging.Handler]:
        return logging.getLogger().handlers

    def _get_handler_truncate_filter(self, handler: logging.Handler) -> TruncateFilter | None:
        for f in handler.filters:
            if isinstance(f, TruncateFilter):
                return f
        return None

    def _has_truncate_filter_on_handlers(self) -> bool:
        return any(
            self._get_handler_truncate_filter(h) for h in self._get_root_handlers()
        )

    def test_nvr_debug_false_no_filter(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="false")
        assert not self._has_truncate_filter_on_handlers()

    def test_nvr_debug_true_has_filter_on_handlers(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="true")
        for h in self._get_root_handlers():
            f = self._get_handler_truncate_filter(h)
            assert f is not None
            assert f.name == "reolink_aio.api"

    def test_nvr_debug_full_has_filter_on_handlers(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="full")
        for h in self._get_root_handlers():
            f = self._get_handler_truncate_filter(h)
            assert f is not None
            assert f.name == "reolink_aio"

    def test_custom_max_length(self, tmp_path: str):
        setup_logging(log_dir=str(tmp_path), nvr_debug="true", nvr_debug_max_length=200)
        handler = self._get_root_handlers()[0]
        f = self._get_handler_truncate_filter(handler)
        assert f is not None
        assert f.max_length == 200

    def test_default_max_length(self, tmp_path: str):
        from remander.logging import DEFAULT_NVR_LOG_MAX_LENGTH

        setup_logging(log_dir=str(tmp_path), nvr_debug="true")
        handler = self._get_root_handlers()[0]
        f = self._get_handler_truncate_filter(handler)
        assert f is not None
        assert f.max_length == DEFAULT_NVR_LOG_MAX_LENGTH

    def test_child_logger_records_are_truncated(self, tmp_path: str):
        """Records from reolink_aio.api.data are truncated via handler filter."""
        setup_logging(log_dir=str(tmp_path), nvr_debug="true", nvr_debug_max_length=50)

        handler = self._get_root_handlers()[0]
        f = self._get_handler_truncate_filter(handler)
        assert f is not None

        # Simulate a record from a child logger (reolink_aio.api.data)
        record = logging.LogRecord(
            "reolink_aio.api.data", logging.DEBUG, "", 0, "x" * 200, (), None
        )
        f.filter(record)
        assert "truncated" in record.getMessage()
