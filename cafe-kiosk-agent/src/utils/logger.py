"""
로깅 유틸리티 모듈
애플리케이션 전반의 로깅을 관리합니다.
"""

import logging
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime
import json
from functools import wraps
import asyncio
import traceback

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

from config.settings import settings


class StructuredLogger:
    """구조화된 로깅을 위한 커스텀 로거"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        로거 초기화
        
        Args:
            name: 로거 이름
            log_file: 로그 파일 경로 (선택)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.log_level))
        
        # 기존 핸들러 제거
        self.logger.handlers.clear()
        
        # 포맷터 설정
        if COLORLOG_AVAILABLE:
            formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 파일 핸들러
        if log_file:
            self._setup_file_handler(log_file, formatter)
    
    def _setup_file_handler(self, log_file: str, formatter: logging.Formatter):
        """파일 핸들러 설정"""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """디버그 로그"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """정보 로그"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 로그"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """에러 로그"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """치명적 에러 로그"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """
        로그 메시지 기록
        
        Args:
            level: 로그 레벨
            message: 로그 메시지
            **kwargs: 추가 컨텍스트 정보
        """
        if kwargs:
            extra_info = json.dumps(kwargs, ensure_ascii=False, default=str)
            full_message = f"{message} | {extra_info}"
        else:
            full_message = message
        
        self.logger.log(level, full_message)
    
    def log_order(self, order_id: str, status: str, details: dict):
        """
        주문 관련 로그
        
        Args:
            order_id: 주문 ID
            status: 주문 상태
            details: 주문 상세 정보
        """
        self.info(
            f"Order {order_id}: {status}",
            order_id=order_id,
            status=status,
            **details
        )
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """
        성능 관련 로그
        
        Args:
            operation: 작업 이름
            duration: 소요 시간 (초)
            **kwargs: 추가 정보
        """
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration_seconds=round(duration, 3),
            **kwargs
        )
    
    def log_error_with_traceback(self, message: str, exception: Exception):
        """
        예외 정보와 함께 에러 로그
        
        Args:
            message: 에러 메시지
            exception: 예외 객체
        """
        tb = traceback.format_exc()
        self.error(
            message,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback=tb
        )


def get_logger(name: str, log_file: Optional[str] = None) -> StructuredLogger:
    """
    로거 인스턴스 반환
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 경로 (선택)
        
    Returns:
        StructuredLogger: 로거 인스턴스
    """
    return StructuredLogger(name, log_file)


def log_execution_time(logger: Optional[StructuredLogger] = None):
    """
    함수 실행 시간을 로깅하는 데코레이터
    
    Args:
        logger: 로거 인스턴스
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            try:
                result = await func(*args, **kwargs)
                duration = asyncio.get_event_loop().time() - start_time
                
                if logger:
                    logger.log_performance(
                        operation=func.__name__,
                        duration=duration,
                        function_type="async"
                    )
                
                return result
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                if logger:
                    logger.error(
                        f"Error in {func.__name__}",
                        duration=duration,
                        error=str(e)
                    )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if logger:
                    logger.log_performance(
                        operation=func.__name__,
                        duration=duration,
                        function_type="sync"
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                if logger:
                    logger.error(
                        f"Error in {func.__name__}",
                        duration=duration,
                        error=str(e)
                    )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> StructuredLogger:
    """
    전역 로깅 설정
    
    Args:
        log_level: 로그 레벨
        log_file: 로그 파일 경로
        
    Returns:
        StructuredLogger: 메인 로거 인스턴스
    """
    if log_level:
        logging.basicConfig(level=getattr(logging, log_level.upper()))
    
    # 로그 디렉토리 생성
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # 기본 로그 파일 경로
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = str(log_dir / f"kiosk_{timestamp}.log")
    
    main_logger = get_logger("cafe_kiosk", log_file)
    main_logger.info("Logging system initialized", log_level=settings.log_level)
    
    return main_logger


# 전역 로거 인스턴스
_main_logger: Optional[StructuredLogger] = None


def get_main_logger() -> StructuredLogger:
    """
    메인 로거 인스턴스 반환
    
    Returns:
        StructuredLogger: 메인 로거
    """
    global _main_logger
    if _main_logger is None:
        _main_logger = setup_logging()
    return _main_logger


class LogContext:
    """로깅 컨텍스트 매니저"""
    
    def __init__(self, logger: StructuredLogger, operation: str, **kwargs):
        """
        초기화
        
        Args:
            logger: 로거 인스턴스
            operation: 작업 이름
            **kwargs: 추가 컨텍스트 정보
        """
        self.logger = logger
        self.operation = operation
        self.context = kwargs
        self.start_time = None
    
    async def __aenter__(self):
        """비동기 컨텍스트 진입"""
        self.start_time = asyncio.get_event_loop().time()
        self.logger.info(f"Starting: {self.operation}", **self.context)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 종료"""
        duration = asyncio.get_event_loop().time() - self.start_time
        
        if exc_type is not None:
            self.logger.error(
                f"Failed: {self.operation}",
                duration=duration,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )
        else:
            self.logger.info(
                f"Completed: {self.operation}",
                duration=duration,
                **self.context
            )
        
        return False  # 예외 전파
    
    def __enter__(self):
        """동기 컨텍스트 진입"""
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting: {self.operation}", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """동기 컨텍스트 종료"""
        import time
        duration = time.time() - self.start_time
        
        if exc_type is not None:
            self.logger.error(
                f"Failed: {self.operation}",
                duration=duration,
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )
        else:
            self.logger.info(
                f"Completed: {self.operation}",
                duration=duration,
                **self.context
            )
        
        return False  # 예외 전파
