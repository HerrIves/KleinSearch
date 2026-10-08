import logging
import os
import sys

from config import LOG_FILE_PATH


def setup_logger(name: str = "ka_scrapper") -> logging.Logger:
    """Logger that writes plain messages to the console and timestamped lines to data/scanner.log."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    try:
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8", mode="a")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(file_handler)
    except OSError as e:
        logger.warning(f"Cannot write log file {LOG_FILE_PATH}: {e}")

    return logger


logger = setup_logger()
