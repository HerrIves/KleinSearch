import logging

from logger import setup_logger


def test_setup_logger_returns_logger():
    log = setup_logger("test_subsystem")
    assert isinstance(log, logging.Logger)
    assert log.name == "test_subsystem"


def test_setup_logger_is_idempotent():
    first = setup_logger("test_idempotent")
    second = setup_logger("test_idempotent")
    assert first is second
    assert len(second.handlers) == len(first.handlers)


def test_logger_writes_message(caplog):
    log = setup_logger("test_logging_output")
    with caplog.at_level(logging.INFO):
        log.info("Test message ✓")
    assert "Test message ✓" in caplog.text
