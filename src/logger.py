"""
This module contains logger and notification config for the project.
Responsible for printing and logging errors to a file as well as gathering
a list of errors that come up so can be sent out in a notification.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

import apprise


class ErrorHandler(logging.Handler):
    """
    Custom logging handler to gather errors in a list
    """

    def __init__(self):
        super().__init__()
        self.errors = []

    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self.errors.append(self.format(record))

    def get_errors(self):
        return self.errors


class AppriseNotifier:
    """
    Class to send out notification of errors
    """

    def __init__(self):
        self.apobj = apprise.Apprise()
        self.apobj.add(os.getenv("DISCORD_ENDPOINT"), tag="error")
        self.apobj.add(os.getenv("TEAMS_ENDPOINT"), tag="error")

    def error_notify(self, error_msg: str):
        """
        Send apprise notification of error
        """
        res = self.apobj.notify(
            body=(
                f"{error_msg}Datetime: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}"
            ),
            title="YouTube Transcripts",
            tag="error",
        )
        if not res:
            logger.error(f"Error, could not send apprise notification: {error_msg}")


# Create a custom logger
logger = logging.getLogger("yt-transcript")

# Set the default log level
log_level = os.getenv("LOG_LEVEL", "ERROR").upper()
logger.setLevel(log_level)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(
    "yt-transcript.log", maxBytes=5 * 1024 * 1024, backupCount=3
)  # 5 MB per file, keep 3 backups
error_handler = ErrorHandler()

# Set log level for handlers
console_handler.setLevel(log_level)
file_handler.setLevel(log_level)
error_handler.setLevel(log_level)

# Create formatters and add them to handlers
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

# Prevent the custom logger from propagating messages to the root logger
logger.propagate = False

# Configure the root logger to use the same handlers
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)
root_logger.addHandler(error_handler)
