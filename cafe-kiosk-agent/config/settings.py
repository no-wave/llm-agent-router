"""
전역 설정 모듈
환경변수를 로드하고 애플리케이션 설정을 관리합니다.
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 전역 설정"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Ollama Configuration
    enable_local_model: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "exaone3.5:7.8b"
    
    # System Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    default_language: str = "ko"
    environment: Literal["development", "staging", "production"] = "development"
    
    # Model Selection Strategy
    model_strategy: Literal["auto", "cloud_only", "local_only"] = "auto"
    
    # Performance Settings
    max_concurrent_orders: int = 10
    request_timeout: int = 30
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    # Business Settings
    tax_rate: float = 0.1
    discount_enabled: bool = True
    loyalty_program_enabled: bool = False
    
    # Feature Flags
    enable_recommendations: bool = True
    enable_voice_order: bool = False
    enable_payment_integration: bool = False
    
    # Model Configuration
    gpt_nano_model: str = "gpt-5-nano"
    gpt_mini_model: str = "gpt-5-mini"
    gpt_standard_model: str = "gpt-5"
    
    # Temperature Settings
    classification_temperature: float = 0.0
    extraction_temperature: float = 0.0
    generation_temperature: float = 0.7
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0


@lru_cache()
def get_settings() -> Settings:
    """
    설정 인스턴스를 반환합니다 (싱글톤 패턴)
    
    Returns:
        Settings: 전역 설정 객체
    """
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
