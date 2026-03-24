"""
Logging — every decision gets logged. If you can't reconstruct what happened, you can't improve.
"""
import logging
import os
import config


def setup_logger(name: str = "trading_bot") -> logging.Logger:
    """Create a logger that writes to both console and file."""
    os.makedirs(config.LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    # File handler
    file_handler = logging.FileHandler(os.path.join(config.LOG_DIR, "trading_bot.log"))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger
