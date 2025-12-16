"""
Logging Configuration Module
Centralized logging setup for the application
日志配置 调试
"""
import os
import sys
from pathlib import Path
from loguru import logger


def setup_logging(
    log_dir: str = "logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "00:00",
    retention: str = "30 days"
):
    """
    Configure application logging
    
    Args:
        log_dir: Directory for log files
        console_level: Console log level
        file_level: File log level
        rotation: Log rotation time
        retention: Log retention period
    """
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=console_level,
        colorize=True
    )
    
    # File handler
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        rotation=rotation,
        retention=retention,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
               "{name}:{function}:{line} - {message}",
        level=file_level,
        encoding="utf-8"
    )
    
    logger.info(f"Logging initialized: console={console_level}, file={file_level}")
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


# Performance logging decorator
def log_performance(func):
    """
    Decorator to log function execution time
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function
    """
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        
        logger.debug(
            f"Function {func.__name__} executed in {elapsed:.3f}s"
        )
        return result
    
    return wrapper


# Context manager for logging blocks
class LogBlock:
    """Context manager for logging code blocks"""
    
    def __init__(self, name: str, level: str = "INFO"):
        """
        Initialize log block
        
        Args:
            name: Block name
            level: Log level
        """
        self.name = name
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        """Enter context"""
        self.start_time = __import__('time').time()
        logger.log(self.level, f"Starting: {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        elapsed = __import__('time').time() - self.start_time
        
        if exc_type:
            logger.error(f"Failed: {self.name} after {elapsed:.3f}s - {exc_val}")
        else:
            logger.log(self.level, f"Completed: {self.name} in {elapsed:.3f}s")
        
        return False


# Example usage
if __name__ == "__main__":
    setup_logging()
    
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning")
    logger.error("This is an error")
    
    @log_performance
    def slow_function():
        import time
        time.sleep(1)
        return "Done"
    
    result = slow_function()
    
    with LogBlock("Database operation"):
        # Simulate some work
        import time
        time.sleep(0.5)
