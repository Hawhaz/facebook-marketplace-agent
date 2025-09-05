"""Configuration management for Facebook Marketplace Agent."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_v1_str: str = "/api/v1"
    project_name: str = "Facebook Marketplace Agent"
    version: str = "1.0.0"
    description: str = "Agente autónomo para automatizar publicaciones en Facebook Marketplace"
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24 * 8  # 8 days
    
    # Firebase Configuration
    firebase_project_id: str = Field(default="listup-scraper", env="FIREBASE_PROJECT_ID")
    firebase_credentials_path: str = Field(
        default="./listup-scraper-firebase-adminsdk-fbsvc-8da37a63d1.json",
        env="FIREBASE_CREDENTIALS_PATH"
    )
    firebase_collection_properties: str = Field(default="properties", env="FIREBASE_COLLECTION_PROPERTIES")
    firebase_collection_jobs: str = Field(default="jobs", env="FIREBASE_COLLECTION_JOBS")
    firebase_collection_logs: str = Field(default="system_logs", env="FIREBASE_COLLECTION_LOGS")
    
    # Google Cloud Storage
    gcs_bucket_name: str = Field(default="listup-scraper-images", env="GCS_BUCKET_NAME")
    gcs_credentials_path: str = Field(
        default="./listup-script-runner-key.json",
        env="GCS_CREDENTIALS_PATH"
    )
    
    # Facebook Credentials (Optional - se solicitan por terminal por seguridad)
    facebook_email: Optional[str] = Field(default=None, env="FACEBOOK_EMAIL")
    facebook_password: Optional[str] = Field(default=None, env="FACEBOOK_PASSWORD")
    facebook_headless: bool = Field(default=True, env="FACEBOOK_HEADLESS")
    facebook_timeout: int = Field(default=30000, env="FACEBOOK_TIMEOUT")
    
    # Century21 Scraping Configuration
    scraping_concurrency_limit: int = Field(default=8, env="SCRAPING_CONCURRENCY_LIMIT")
    scraping_timeout: int = Field(default=30000, env="SCRAPING_TIMEOUT")
    scraping_headless: bool = Field(default=True, env="SCRAPING_HEADLESS")
    
    # Image Storage
    image_storage_path: str = Field(default="./images", env="IMAGE_STORAGE_PATH")
    max_image_size_mb: int = Field(default=10, env="MAX_IMAGE_SIZE_MB")
    supported_image_formats: list[str] = ["jpg", "jpeg", "png", "webp"]
    
    # Google Cloud Firestore Cache (Optional)
    use_firestore_cache: bool = Field(default=True, env="USE_FIRESTORE_CACHE")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")  # 1 hour
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Monitoring
    enable_metrics: bool = Field(default=False, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8001, env="METRICS_PORT")
    
    # Facebook Agent Configuration
    facebook_slow_mo: int = Field(default=0, env="FACEBOOK_SLOW_MO")
    
    # Logging Configuration
    log_file: str = Field(default="./logs/app.log", env="LOG_FILE")
    
    # Rate Limiting Configuration
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
