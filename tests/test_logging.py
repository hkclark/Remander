"""Tests for logging configuration — NVR debug levels."""

import logging

import pytest

from remander.logging import setup_logging


@pytest.fixture(autouse=True)
def _reset_loggers():
    """Reset reolink_aio logger levels after each test."""
    yield
    for name in ("reolink_aio", "reolink_aio.api", "reolink_aio.baichuan"):
        logging.getLogger(name).setLevel(logging.NOTSET)


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
