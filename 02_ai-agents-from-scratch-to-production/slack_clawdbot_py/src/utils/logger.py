import logging
import sys
import os
from typing import Optional

# ANSI color codes for clean, professional console logs
COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[35m",  # Magenta
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m"
}

class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, COLORS["RESET"])
        reset = COLORS["RESET"]
        dim = COLORS["DIM"]
        bold = COLORS["BOLD"]
        
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:<7}{reset}"
        module_name = f"{dim}[{record.name}]{reset}"
        message = record.getMessage()
        
        return f"{dim}{timestamp}{reset} {level} {module_name} {message}"

def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """Setup root application logger."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    root_logger = logging.getLogger("slack_bot")
    root_logger.setLevel(level)
    
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(handler)
        root_logger.propagate = False
        
    return root_logger

def create_module_logger(module_name: str) -> logging.Logger:
    """Create a sub-logger for a specific module."""
    return logging.getLogger(f"slack_bot.{module_name}")

def get_logger() -> logging.Logger:
    return logging.getLogger("slack_bot")
