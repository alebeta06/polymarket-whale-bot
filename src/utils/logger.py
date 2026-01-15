"""
Logging configuration for the bot.
"""
import sys
from pathlib import Path
from loguru import logger
from src.config import get_settings


def setup_logger():
    """Configure loguru logger"""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # File handler with rotation
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "polymarket_bot.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=settings.log_level,
        rotation=f"{settings.log_max_size} MB",
        retention="7 days",
        compression="zip"
    )
    
    # Separate file for errors
    logger.add(
        log_dir / "errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation=f"{settings.log_max_size} MB",
        retention="30 days",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Logger initialized")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Dry run mode: {settings.dry_run}")
    
    return logger


# Global logger instance
log = setup_logger()
