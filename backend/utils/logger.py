"""
Logging configuration for Translator Helper backend.
"""

import logging
from pathlib import Path

def setup_logger(
    name: str = "translator-helper",
    level: int = logging.INFO,
    log_dir: str = "outputs"
) -> logging.Logger:
    """
    Set up and return a configured logger that writes to a file.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # File handler
    file_handler = logging.FileHandler(
        log_path / f"{name}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # Format: [2025-12-21 10:30:45] [INFO] [module_name] Message
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "translator-helper") -> logging.Logger:
    """
    Get an existing logger or create a new one with default settings.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
