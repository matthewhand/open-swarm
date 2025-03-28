import logging
import sys
from swarm.settings import Settings, LogFormat

# Cache for initialized loggers to avoid adding handlers multiple times
_initialized_loggers = set()

def setup_logging(logger_name: str | None = None, level: str | int = Settings().log_level, force_reconfigure: bool = False) -> logging.Logger:
    """
    Configures and returns a logger instance. Ensures handlers are not duplicated
    and prevents propagation to avoid duplicate messages from parent loggers.

    Args:
        logger_name: Name of the logger. If None, configures the root logger.
        level: Logging level (e.g., 'DEBUG', 'INFO', logging.DEBUG).
        force_reconfigure: If True, remove existing handlers before adding new ones.

    Returns:
        Configured logger instance.
    """
    log_level = logging.getLevelName(level.upper()) if isinstance(level, str) else level

    logger = logging.getLogger(logger_name)
    logger_id = logger_name if logger_name is not None else "root"

    # Check if logger (by name) is already initialized and reconfiguration is not forced
    if logger_id in _initialized_loggers and not force_reconfigure:
        if logger.level != log_level:
             logger.setLevel(log_level)
        return logger

    # If forcing reconfigure or first time, remove existing handlers
    if force_reconfigure or logger_id not in _initialized_loggers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        if logger_name is None:
             root_logger = logging.getLogger()
             for handler in root_logger.handlers[:]:
                  root_logger.removeHandler(handler)

    # Set the desired level on the logger
    logger.setLevel(log_level)

    # Prevent propagation for non-root loggers
    if logger_name is not None:
        logger.propagate = False
    else:
        logger.propagate = True # Root logger should propagate if needed by other libraries

    # Add the stream handler if no handlers exist after potential removal
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        log_format_enum = Settings().log_format
        formatter = logging.Formatter(log_format_enum.value)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _initialized_loggers.add(logger_id)

    # --- Lower level for specific noisy loggers ---
    logging.getLogger('swarm.extensions.config.config_loader').setLevel(logging.ERROR) # Make config loader quieter by default

    return logger
