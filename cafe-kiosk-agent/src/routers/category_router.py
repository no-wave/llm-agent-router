"""
카테고리 라우터 모듈
주문을 메뉴 카테고리별로 라우팅합니다.
"""

import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum

from config.menu_database import (
    MenuCategory,
    get_menu_by_category,
    get_all_menu_names,
)
from src.services.llm_service import get_llm_service
from src.utils.logger import get_logger, LogContext
from src.utils.validators import OrderValidator, TextNormalizer


logger = get_logger(__name__)


class RouteDecision:
    """라우팅 결정 결과"""
    
    def __init__(
        self,
        category: MenuCategory,
        confidence: float,
        reasoning: str = ""
    ):
        """
        초기화
        
        Args:
            category: 선택된 카테고리
            confidence: 신뢰도 (0.0 ~ 1.0)
            reasoning: 선택 이유
        """
        self.category = category
        self.confidence = confidence
        self.reasoning = reasoning
    
    def __repr__(self) -> str:
        return f"RouteDecision(category={self.category.value}, confidence={self.confidence:.2f})"


class CategoryRouter:
    """카테고리 라우팅 에이전트"""
    
    def __init__(self):
        """초기화"""
        self.llm_service = None
        self.category_keywords = self._build_category_keywords()
        logger.info("Category Router initialized")
    
    def _build_category_keywords(self) -> Dict[MenuCategory, List[str]]:
        """
        카테고리별 키워드 맵 생성
        
        Returns:
            Dict[MenuCategory, List[str]]: 카테고리-키워드 맵
        """
        return {
            MenuCategory.BEVERAGE: [
                "음료", "커피", "라떼", "아메리카노", "주스", "티", "차",
                "마시", "drink", "coffee", "음료수", "시원한", "따뜻한"
            ],
            MenuCategory.DESSERT: [
                "디저트", "케이크", "빵", "쿠키", "마카롱", "와플", "달콤한",
                "dessert", "sweet", "간식", "후식", "타르트", "스콘"
            ],
            MenuCategory.MEAL: [
                "식사", "끼니", "샌드위치", "파스타", "샐러드", "피자",
                "meal", "food", "먹을", "배고", "점심", "저녁", "아침"
            ]
        }
    
    async def _ensure_llm_service(self):
        """LLM 서비스 초기화 확인"""
        if self.llm_service is None:
            self.llm_service = await get_llm_service()
    
    async def route(self, order_text: str) -> RouteDecision:
        """
        주문 텍스트를 카테고리로 라우팅
        
        Args:
            order_text: 주문 텍스트
            
        Returns:
            RouteDecision: 라우팅 결정
        """
        async with LogContext(logger, "category_routing", order_text=order_text[:50]):
            # 텍스트 정규화
            normalized_text = TextNormalizer.normalize_whitespace(order_text)
            
            # 키워드 기반 빠른 분류 시도
            keyword_result = self._classify_by_keywords(normalized_text)
            
            if keyword_result and keyword_result.confidence > 0.8:
                logger.info(
                    "Fast keyword-based classification",
                    category=keyword_result.category.value,
                    confidence=keyword_result.confidence
                )
                return keyword_result
            
            # LLM 기반 분류
            await self._ensure_llm_service()
            
            try:
                category_str = await self.llm_service.classify_category(normalized_text)
                category = self._parse_category(category_str)
                
                logger.info(
                    "LLM-based classification",
                    category=category.value,
                    raw_output=category_str
                )
                
                return RouteDecision(
                    category=category,
                    confidence=0.9,
                    reasoning="LLM classification"
                )
            
            except Exception as e:
                logger.error(
                    "Failed to classify category",
                    error=str(e)
                )
                
                # 폴백: 기본 카테고리
                return RouteDecision(
                    category=MenuCategory.BEVERAGE,
                    confidence=0.5,
                    reasoning="Fallback to default category"
                )
    
    def _classify_by_keywords(self, text: str) -> Optional[RouteDecision]:
        """
        키워드 기반 빠른 분류
        
        Args:
            text: 입력 텍스트
            
        Returns:
            Optional[RouteDecision]: 라우팅 결정 또는 None
        """
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[category] = score
        
        if not any(scores.values()):
            return None
        
        # 가장 높은 점수의 카테고리
        max_category = max(scores, key=scores.get)
        max_score = scores[max_category]
        total_score = sum(scores.values())
        
        # 신뢰도 계산
        confidence = max_score / total_score if total_score > 0 else 0
        
        if confidence < 0.6:
            return None
        
        return RouteDecision(
            category=max_category,
            confidence=confidence,
            reasoning=f"Keyword matching (score: {max_score}/{total_score})"
        )
    
    def _parse_category(self, category_str: str) -> MenuCategory:
        """
        문자열을 MenuCategory로 파싱
        
        Args:
            category_str: 카테고리 문자열
            
        Returns:
            MenuCategory: 파싱된 카테고리
        """
        category_map = {
            "음료": MenuCategory.BEVERAGE,
            "beverage": MenuCategory.BEVERAGE,
            "디저트": MenuCategory.DESSERT,
            "dessert": MenuCategory.DESSERT,
            "식사": MenuCategory.MEAL,
            "meal": MenuCategory.MEAL,
        }
        
        category_str = category_str.strip().lower()
        
        for key, value in category_map.items():
            if key in category_str:
                return value
        
        # 기본값
        logger.warning(f"Unknown category string: {category_str}, using default")
        return MenuCategory.BEVERAGE
    
    async def route_batch(
        self,
        order_texts: List[str]
    ) -> List[RouteDecision]:
        """
        여러 주문을 배치로 라우팅
        
        Args:
            order_texts: 주문 텍스트 리스트
            
        Returns:
            List[RouteDecision]: 라우팅 결정 리스트
        """
        async with LogContext(logger, "batch_category_routing", count=len(order_texts)):
            tasks = [self.route(text) for text in order_texts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리
            decisions = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to route order {i}",
                        error=str(result)
                    )
                    # 기본 카테고리로 폴백
                    decisions.append(RouteDecision(
                        category=MenuCategory.BEVERAGE,
                        confidence=0.5,
                        reasoning="Error fallback"
                    ))
                else:
                    decisions.append(result)
            
            return decisions
    
    async def get_available_menus(
        self,
        category: MenuCategory
    ) -> List[str]:
        """
        카테고리의 사용 가능한 메뉴 목록 반환
        
        Args:
            category: 메뉴 카테고리
            
        Returns:
            List[str]: 메뉴 이름 리스트
        """
        menu_dict = get_menu_by_category(category)
        return [
            name for name, item in menu_dict.items()
            if item.available
        ]
    
    async def validate_category_items(
        self,
        category: MenuCategory,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        카테고리에 속한 항목들만 필터링
        
        Args:
            category: 카테고리
            items: 주문 항목 리스트
            
        Returns:
            List[Dict[str, Any]]: 필터링된 항목 리스트
        """
        valid_items = []
        available_menus = await self.get_available_menus(category)
        
        for item in items:
            menu_name = item.get("menu")
            
            if menu_name in available_menus:
                valid_items.append(item)
            else:
                logger.warning(
                    f"Menu not available in category",
                    menu=menu_name,
                    category=category.value
                )
        
        return valid_items
    
    def get_category_stats(self) -> Dict[str, int]:
        """
        카테고리별 통계 (메뉴 개수)
        
        Returns:
            Dict[str, int]: 카테고리별 메뉴 개수
        """
        stats = {}
        
        for category in MenuCategory:
            menu_dict = get_menu_by_category(category)
            stats[category.value] = len(menu_dict)
        
        return stats


# 싱글톤 인스턴스
_category_router: Optional[CategoryRouter] = None


def get_category_router() -> CategoryRouter:
    """
    카테고리 라우터 인스턴스 반환
    
    Returns:
        CategoryRouter: 카테고리 라우터 인스턴스
    """
    global _category_router
    if _category_router is None:
        _category_router = CategoryRouter()
    return _category_router
