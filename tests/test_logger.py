import logging

from core import logger as logger_module


def test_configure_logging_keeps_file_and_console_handlers(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    latest_log = logs_dir / "latest.txt"
    monkeypatch.setattr(logger_module, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(logger_module, "LATEST_LOG_PATH", latest_log)

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    try:
        logger_module.configure_logging()
        handler_names = {
            getattr(handler, "name", type(handler).__name__)
            for handler in root_logger.handlers
        }

        assert "home-mini-git-latest-file" in handler_names
        assert "home-mini-git-console" in handler_names

        logging.getLogger("tests.logger").info("console and file logging works")
        for handler in root_logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        assert latest_log.exists()
        assert "console and file logging works" in latest_log.read_text(
            encoding="utf-8"
        )
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root_logger.addHandler(handler)
