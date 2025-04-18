# src/swarm/config/utils/logger.py

import logging
from typing import Optional

def setup_logger(name: str, level: int = logging.DEBUG, log_file: Optional[str] = None) -> logging.Logger:
    """
    Sets up and returns a logger with the specified name and level.

    Args:
        name (str): The name of the logger.
        level (int, optional): Logging level. Defaults to logging.DEBUG.
        log_file (str, optional): File path to log to. If None, logs to console. Defaults to None.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent adding multiple handlers to the logger
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger
