"""
logging_config.py
------------------

Centralized logging configuration for the trading bot.

Behavior:
    - Everything at DEBUG level and above is written to logs/trading_bot.log
      (full detail: requests, responses, stack traces).
    - Only INFO level and above is printed to the console, in a compact,
      human-readable format, so normal usage isn't noisy.

Call `setup_logging()` once, as early as possible (e.g. at the top of cli.py).
Every other module should just do:

    import logging
    logger = logging.getLogger(__name__)

and logging will flow through the handlers configured here.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Directory where log files live. Created automatically if missing.
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_LOGGING_CONFIGURED = False


def setup_logging(log_dir: str = LOG_DIR, log_file: str = LOG_FILE) -> None:
    """
    Configure the root logger with two handlers:
      1. RotatingFileHandler -> DEBUG and above -> logs/trading_bot.log
      2. StreamHandler       -> INFO and above  -> console (stdout)

    Safe to call multiple times; configuration is only applied once per process.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Root must allow DEBUG through to handlers.

    # --- File handler: verbose, persistent, rotates at 5MB, keeps 3 backups ---
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # --- Console handler: concise, human readable, INFO and above only ---
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Quiet down noisy third-party libraries on the console; they still get
    # written to the DEBUG log file via the root logger's file handler.
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    _LOGGING_CONFIGURED = True
