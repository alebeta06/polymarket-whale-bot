"""
Configuration module for Polymarket Arbitrage Bot.
Loads and validates environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    """Bot configuration from environment variables"""
    
    # API Credentials
    polymarket_api_key: str = Field(..., env="POLYMARKET_API_KEY")
    polymarket_api_secret: str = Field(..., env="POLYMARKET_API_SECRET")
    polymarket_api_passphrase: str = Field(..., env="POLYMARKET_API_PASSPHRASE")
    
    # Wallet Configuration
    private_key: str = Field(..., env="PRIVATE_KEY")
    eoa_address: str = Field(..., env="EOA_ADDRESS")
    proxy_wallet_address: str = Field(..., env="PROXY_WALLET_ADDRESS")
    polygon_rpc_url: str = Field(default="https://polygon-rpc.com", env="POLYGON_RPC_URL")
    
    # Trading Parameters
    dry_run: bool = Field(default=True, env="DRY_RUN")
    max_position_size_percent: float = Field(default=0.15, env="MAX_POSITION_SIZE_PERCENT")
    daily_stop_loss_percent: float = Field(default=0.10, env="DAILY_STOP_LOSS_PERCENT")
    min_profit_percent: float = Field(default=0.02, env="MIN_PROFIT_PERCENT")
    polymarket_fee_percent: float = Field(default=0.02, env="POLYMARKET_FEE_PERCENT")

    # Whale-trade gating + paper trading
    min_whale_trade_usd: float = Field(default=500.0, env="MIN_WHALE_TRADE_USD")
    max_whale_trade_age_seconds: float = Field(default=600.0, env="MAX_WHALE_TRADE_AGE_SECONDS")
    paper_starting_balance_usd: float = Field(default=1000.0, env="PAPER_STARTING_BALANCE_USD")
    max_per_copy_trade_usd: float = Field(default=200.0, env="MAX_PER_COPY_TRADE_USD")
    # Run reconcile() every N completed poll cycles. 0 disables in-loop reconciling.
    reconcile_every_n_polls: int = Field(default=10, env="RECONCILE_EVERY_N_POLLS")
    
    # Market Scanner
    min_market_volume: float = Field(default=10000, env="MIN_MARKET_VOLUME")
    scan_categories: str = Field(default="Politics,Crypto,Sports", env="SCAN_CATEGORIES")
    market_refresh_interval: int = Field(default=300, env="MARKET_REFRESH_INTERVAL")
    
    # WebSocket
    websocket_url: str = Field(
        default="wss://ws-subscriptions-clob.polymarket.com",
        env="WEBSOCKET_URL"
    )
    use_websocket: bool = Field(default=True, env="USE_WEBSOCKET")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_max_size: int = Field(default=100, env="LOG_MAX_SIZE")
    
    # Monitoring
    enable_telegram: bool = Field(default=False, env="ENABLE_TELEGRAM")
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID")
    
    # Advanced
    rate_limit_buffer: float = Field(default=0.8, env="RATE_LIMIT_BUFFER")
    use_relayer: bool = Field(default=False, env="USE_RELAYER")
    relayer_api_key: str = Field(default="", env="RELAYER_API_KEY")
    relayer_api_key_address: str = Field(default="", env="RELAYER_API_KEY_ADDRESS")
    order_batch_size: int = Field(default=5, env="ORDER_BATCH_SIZE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("max_position_size_percent", "daily_stop_loss_percent", "min_profit_percent")
    def validate_percentages(cls, v):
        if not 0 < v <= 1:
            raise ValueError("Percentage must be between 0 and 1")
        return v
    
    @validator("private_key")
    def validate_private_key(cls, v):
        if not v.startswith("0x") or len(v) != 66:
            raise ValueError("Private key must start with 0x and be 66 characters long")
        return v
    
    @validator("eoa_address", "proxy_wallet_address")
    def validate_address(cls, v):
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Address must start with 0x and be 42 characters long")
        return v
    
    def get_categories_list(self) -> List[str]:
        """Get scan categories as a list"""
        return [cat.strip() for cat in self.scan_categories.split(",")]


# Global settings instance
settings = None


def load_settings() -> Settings:
    """Load settings from .env file"""
    global settings
    if settings is None:
        # Check if .env exists
        env_path = Path(".env")
        if not env_path.exists():
            raise FileNotFoundError(
                ".env file not found. Copy .env.example to .env and configure it."
            )
        settings = Settings()
    return settings


def get_settings() -> Settings:
    """Get current settings instance"""
    global settings
    if settings is None:
        settings = load_settings()
    return settings
