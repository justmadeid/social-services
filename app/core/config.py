import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database settings
    database_url: str = "mysql+aiomysql://scraper_user:scraper_pass@localhost:3306/twitter_scraper"
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "scraper_user"
    db_password: str = "scraper_pass"
    db_name: str = "twitter_scraper"
    db_root_password: str = "root_password"  # Added missing field
    
    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Celery settings
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # Security settings
    secret_key: str = "your-secret-key-here"
    encryption_key: str = "your-32-char-encryption-key-here"
    api_key: str = "your-api-key-here"
    
    # Application settings
    log_level: str = "INFO"
    environment: str = "development"
    
    # Cache settings
    cache_ttl_user_data: int = 3600  # 1 hour
    cache_ttl_timeline_data: int = 21600  # 6 hours
    cache_ttl_task_result: int = 86400  # 24 hours
    
    # Twitter scraping settings
    default_tweet_count: int = 80
    min_tweet_count: int = 20
    max_tweet_count: int = 100
    scraping_timeout: int = 300  # 5 minutes
    
    # API settings
    api_v1_str: str = "/api/v1"
    project_name: str = "Twitter Scraper API"
    project_version: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
