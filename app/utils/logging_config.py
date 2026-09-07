"""
Logging Configuration with Automatic Credential Masking
"""

import re
import logging
import sys

# Regex to match URLs containing user:pass@
CREDENTIAL_REGEX = re.compile(r"://([^:@\s]+):([^@\s]+)@")

class CredentialSanitizingFormatter(logging.Formatter):
    """Logging formatter that automatically strips credentials from log messages."""
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        # Replace ://username:password@ with ://username:***@
        sanitized = CREDENTIAL_REGEX.sub(r"://\1:***@", original)
        return sanitized

def get_logger(name: str = "camera_platform") -> logging.Logger:
    """Returns a configured logger with credential sanitization enabled."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = CredentialSanitizingFormatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger
