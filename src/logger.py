"""
Logging configuration for the MLOps Clinical Trials platform.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from loguru import logger
import structlog


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages toward loguru sinks."""
    
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = False,
    intercept_standard_logging: bool = True
) -> None:
    """
    Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_logs: Whether to use JSON format for logs
        intercept_standard_logging: Whether to intercept standard logging
    """
    # Remove default logger
    logger.remove()
    
    # Configure log format
    if json_logs:
        log_format = (
            "{"
            '"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}"'
            "}"
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=level,
        colorize=not json_logs,
        serialize=json_logs,
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format=log_format,
            level=level,
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            serialize=json_logs,
        )
    
    # Intercept standard logging if requested
    if intercept_standard_logging:
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        
        # Intercept specific loggers
        for logger_name in ["uvicorn", "fastapi", "sqlalchemy", "kubernetes"]:
            logging.getLogger(logger_name).handlers = [InterceptHandler()]


def get_logger(name: str) -> "loguru.Logger":
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logger.bind(module=name)


def configure_structlog() -> None:
    """Configure structlog for structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(30),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


# Initialize logging on import
setup_logging()
configure_structlog()
