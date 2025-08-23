# src/logging_handler.py

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Create logs directory if it doesn't exist
def configure_logging(log_level=logging.INFO, log_to_file=True):
    """Configure application-wide logging settings.
    
    Parameters
    ----------
    log_level : int
        The logging level (default: logging.INFO)
    log_to_file : bool
        Whether to log to a file in addition to console (default: True)
    """
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file:
        # Create logs directory
        log_dir = Path(os.path.dirname(__file__), os.pardir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler (10 MB max size, keep 5 backups)
        log_file = os.path.join(log_dir, "datascope.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

# Get a logger for a specific module
def get_logger(name):
    """Get a logger for a specific module.
    
    Parameters
    ----------
    name : str
        The name of the module (typically __name__)
        
    Returns
    -------
    logging.Logger
        A logger instance for the specified module
    """
    return logging.getLogger(name)

# Test function
def test_logger():
    """Test the logger configuration."""
    logger = get_logger(__name__)
    logger.debug("Debug message - only visible at DEBUG level")
    logger.info("Info message - visible at INFO level and below")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    return "Logger test complete. Check logs for output."
