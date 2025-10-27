"""
입력 검증 유틸리티 모듈
사용자 입력과 데이터를 검증합니다.
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from config.menu_database import (
    get_menu_item,
    get_all_menu_names,
    MenuCategory,
    SizeOption,
    TemperatureOption
)


@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    message: str
    data: Optional[Any] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class OrderValidator:
    """주문 검증 클래스"""
    
    @staticmethod
    def validate_order_text(order_text: str) -> ValidationResult:
        """
        주문 텍스트 검증
        
        Args:
            order_text: 주문 텍스트
            
        Returns:
            ValidationResult: 검증 결과
        """
        if not order_text or not order_text.strip():
            return ValidationResult(
                is_valid=False,
                message="주문 내용이 비어있습니다.",
                errors=["empty_order"]
            )
        
        # 최소 길이 검증
        if len(order_text.strip()) < 2:
            return ValidationResult(
                is_valid=False,
                message="주문 내용이 너무 짧습니다.",
                errors=["order_too_short"]
            )
        
        # 최대 길이 검증
        if len(order_text) > 500:
            return ValidationResult(
                is_valid=False,
                message="주문 내용이 너무 깁니다. (최대 500자)",
                errors=["order_too_long"]
            )
        
        return ValidationResult(
            is_valid=True,
            message="유효한 주문입니다.",
            data=order_text.strip()
        )
    
    @staticmethod
    def validate_menu_item(menu_name: str, category: Optional[MenuCategory] = None) -> ValidationResult:
        """
        메뉴 아이템 검증
        
        Args:
            menu_name: 메뉴 이름
            category: 메뉴 카테고리 (선택)
            
        Returns:
            ValidationResult: 검증 결과
        """
        menu_item = get_menu_item(menu_name, category)
        
        if menu_item is None:
            return ValidationResult(
                is_valid=False,
                message=f"'{menu_name}' 메뉴를 찾을 수 없습니다.",
                errors=["menu_not_found"]
            )
        
        if not menu_item.available:
            return ValidationResult(
                is_valid=False,
                message=f"'{menu_name}' 메뉴는 현재 품절입니다.",
                errors=["menu_unavailable"]
            )
        
        return ValidationResult(
            is_valid=True,
            message="유효한 메뉴입니다.",
            data=menu_item
        )
    
    @staticmethod
    def validate_quantity(quantity: int) -> ValidationResult:
        """
        수량 검증
        
        Args:
            quantity: 주문 수량
            
        Returns:
            ValidationResult: 검증 결과
        """
        if quantity < 1:
            return ValidationResult(
                is_valid=False,
                message="수량은 1개 이상이어야 합니다.",
                errors=["invalid_quantity"]
            )
        
        if quantity > 99:
            return ValidationResult(
                is_valid=False,
                message="한 번에 최대 99개까지 주문 가능합니다.",
                errors=["quantity_too_large"]
            )
        
        return ValidationResult(
            is_valid=True,
            message="유효한 수량입니다.",
            data=quantity
        )
    
    @staticmethod
    def validate_size(size: str, menu_name: str) -> ValidationResult:
        """
        사이즈 옵션 검증
        
        Args:
            size: 사이즈 옵션
            menu_name: 메뉴 이름
            
        Returns:
            ValidationResult: 검증 결과
        """
        # 사이즈 정규화
        size_map = {
            "톨": SizeOption.TALL,
            "tall": SizeOption.TALL,
            "그란데": SizeOption.GRANDE,
            "grande": SizeOption.GRANDE,
            "벤티": SizeOption.VENTI,
            "venti": SizeOption.VENTI,
        }
        
        normalized_size = size_map.get(size.lower())
        
        if normalized_size is None:
            return ValidationResult(
                is_valid=False,
                message=f"'{size}'는 유효하지 않은 사이즈입니다.",
                errors=["invalid_size"]
            )
        
        # 메뉴의 사이즈 옵션 확인
        menu_item = get_menu_item(menu_name)
        if menu_item and normalized_size not in menu_item.size_options:
            return ValidationResult(
                is_valid=False,
                message=f"'{menu_name}' 메뉴는 '{size}' 사이즈를 제공하지 않습니다.",
                errors=["size_not_available"]
            )
        
        return ValidationResult(
            is_valid=True,
            message="유효한 사이즈입니다.",
            data=normalized_size
        )
    
    @staticmethod
    def validate_temperature(temperature: str, menu_name: str) -> ValidationResult:
        """
        온도 옵션 검증
        
        Args:
            temperature: 온도 옵션
            menu_name: 메뉴 이름
            
        Returns:
            ValidationResult: 검증 결과
        """
        # 온도 정규화
        temp_map = {
            "뜨거운": TemperatureOption.HOT,
            "핫": TemperatureOption.HOT,
            "hot": TemperatureOption.HOT,
            "차가운": TemperatureOption.ICE,
            "아이스": TemperatureOption.ICE,
            "ice": TemperatureOption.ICE,
            "iced": TemperatureOption.ICE,
        }
        
        normalized_temp = temp_map.get(temperature.lower())
        
        if normalized_temp is None:
            return ValidationResult(
                is_valid=False,
                message=f"'{temperature}'는 유효하지 않은 온도 옵션입니다.",
                errors=["invalid_temperature"]
            )
        
        # 메뉴의 온도 옵션 확인
        menu_item = get_menu_item(menu_name)
        if menu_item and normalized_temp not in menu_item.temperature_options:
            return ValidationResult(
                is_valid=False,
                message=f"'{menu_name}' 메뉴는 '{temperature}' 옵션을 제공하지 않습니다.",
                errors=["temperature_not_available"]
            )
        
        return ValidationResult(
            is_valid=True,
            message="유효한 온도 옵션입니다.",
            data=normalized_temp
        )
    
    @staticmethod
    def validate_order_items(items: List[Dict[str, Any]]) -> ValidationResult:
        """
        주문 항목 리스트 검증
        
        Args:
            items: 주문 항목 리스트
            
        Returns:
            ValidationResult: 검증 결과
        """
        if not items:
            return ValidationResult(
                is_valid=False,
                message="주문 항목이 없습니다.",
                errors=["no_items"]
            )
        
        errors = []
        validated_items = []
        
        for idx, item in enumerate(items):
            # 필수 필드 확인
            if "menu" not in item:
                errors.append(f"항목 {idx + 1}: 메뉴 이름이 없습니다.")
                continue
            
            if "quantity" not in item:
                errors.append(f"항목 {idx + 1}: 수량이 없습니다.")
                continue
            
            # 메뉴 검증
            menu_result = OrderValidator.validate_menu_item(item["menu"])
            if not menu_result.is_valid:
                errors.append(f"항목 {idx + 1}: {menu_result.message}")
                continue
            
            # 수량 검증
            qty_result = OrderValidator.validate_quantity(item["quantity"])
            if not qty_result.is_valid:
                errors.append(f"항목 {idx + 1}: {qty_result.message}")
                continue
            
            # 사이즈 검증 (선택적)
            if "size" in item and item["size"]:
                size_result = OrderValidator.validate_size(item["size"], item["menu"])
                if not size_result.is_valid:
                    errors.append(f"항목 {idx + 1}: {size_result.message}")
                    continue
            
            # 온도 검증 (선택적)
            if "temperature" in item and item["temperature"]:
                temp_result = OrderValidator.validate_temperature(item["temperature"], item["menu"])
                if not temp_result.is_valid:
                    errors.append(f"항목 {idx + 1}: {temp_result.message}")
                    continue
            
            validated_items.append(item)
        
        if errors:
            return ValidationResult(
                is_valid=False,
                message="일부 주문 항목이 유효하지 않습니다.",
                errors=errors
            )
        
        return ValidationResult(
            is_valid=True,
            message="모든 주문 항목이 유효합니다.",
            data=validated_items
        )


class TextNormalizer:
    """텍스트 정규화 클래스"""
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        공백 정규화
        
        Args:
            text: 입력 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        return re.sub(r'\s+', ' ', text.strip())
    
    @staticmethod
    def normalize_numbers(text: str) -> str:
        """
        숫자 표현 정규화
        
        Args:
            text: 입력 텍스트
            
        Returns:
            str: 정규화된 텍스트
        """
        number_map = {
            "한": "1", "하나": "1",
            "두": "2", "둘": "2",
            "세": "3", "셋": "3",
            "네": "4", "넷": "4",
            "다섯": "5",
            "여섯": "6",
            "일곱": "7",
            "여덟": "8",
            "아홉": "9",
            "열": "10",
        }
        
        for korean, digit in number_map.items():
            text = re.sub(rf'\b{korean}\b', digit, text)
        
        return text
    
    @staticmethod
    def normalize_menu_name(text: str) -> str:
        """
        메뉴 이름 정규화
        
        Args:
            text: 입력 텍스트
            
        Returns:
            str: 정규화된 메뉴 이름
        """
        # 공백 제거
        text = text.strip()
        
        # 일반적인 변형 처리
        variations = {
            "아메": "아메리카노",
            "라떼": "카페라떼",
            "까페라떼": "카페라떼",
            "카페라테": "카페라떼",
            "카푸": "카푸치노",
            "마끼": "카라멜마끼아또",
            "마끼아또": "카라멜마끼아또",
        }
        
        for short, full in variations.items():
            if short in text:
                text = text.replace(short, full)
        
        return text
    
    @staticmethod
    def extract_quantity_from_text(text: str) -> Optional[int]:
        """
        텍스트에서 수량 추출
        
        Args:
            text: 입력 텍스트
            
        Returns:
            Optional[int]: 추출된 수량 또는 None
        """
        # 숫자 + 단위 패턴 (예: 2잔, 3개, 1인분)
        pattern = r'(\d+)\s*(?:잔|개|인분|조각|판)'
        match = re.search(pattern, text)
        
        if match:
            return int(match.group(1))
        
        # 단순 숫자 패턴
        pattern = r'\b(\d+)\b'
        match = re.search(pattern, text)
        
        if match:
            return int(match.group(1))
        
        return None


class InputSanitizer:
    """입력 살균 클래스"""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        텍스트 살균 (위험한 문자 제거)
        
        Args:
            text: 입력 텍스트
            
        Returns:
            str: 살균된 텍스트
        """
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # 스크립트 제거
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        
        # SQL 인젝션 패턴 제거 (기본적인 것만)
        dangerous_patterns = [
            r';\s*DROP\s+TABLE',
            r';\s*DELETE\s+FROM',
            r';\s*UPDATE\s+',
            r'--',
            r'/\*',
            r'\*/',
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def validate_safe_characters(text: str) -> bool:
        """
        안전한 문자만 포함되어 있는지 확인
        
        Args:
            text: 입력 텍스트
            
        Returns:
            bool: 안전 여부
        """
        # 허용된 문자: 한글, 영문, 숫자, 공백, 일부 특수문자
        pattern = r'^[가-힣a-zA-Z0-9\s\.,!?()+-]*$'
        return bool(re.match(pattern, text))
