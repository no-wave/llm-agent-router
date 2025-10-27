"""
추천 에이전트 모듈
메뉴 추천 및 제안을 관리합니다.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum

from config.menu_database import (
    MenuCategory,
    get_menu_by_category,
    search_menu,
    MenuItem
)
from config.settings import settings
from src.services import get_llm_service, get_order_service
from src.utils import get_logger, LogContext


logger = get_logger(__name__)


class TimeOfDay(str, Enum):
    """시간대"""
    MORNING = "morning"      # 06:00 - 11:00
    BRUNCH = "brunch"        # 11:00 - 14:00
    AFTERNOON = "afternoon"  # 14:00 - 17:00
    EVENING = "evening"      # 17:00 - 21:00
    NIGHT = "night"          # 21:00 - 06:00


class Weather(str, Enum):
    """날씨"""
    HOT = "hot"
    COLD = "cold"
    RAINY = "rainy"
    NORMAL = "normal"


@dataclass
class Recommendation:
    """추천 결과"""
    items: List[MenuItem]
    reason: str
    confidence: float
    category: Optional[MenuCategory] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "items": [
                {
                    "name": item.name,
                    "category": item.category.value,
                    "price": item.base_price,
                    "description": item.description
                }
                for item in self.items
            ],
            "reason": self.reason,
            "confidence": self.confidence,
            "category": self.category.value if self.category else None
        }


class RecommendationAgent:
    """추천 에이전트"""
    
    def __init__(self):
        """초기화"""
        self.llm_service = None
        self.order_service = get_order_service()
        
        # 시간대별 추천 메뉴
        self.time_recommendations = {
            TimeOfDay.MORNING: ["아메리카노", "크로와상", "베이글"],
            TimeOfDay.BRUNCH: ["샌드위치", "샐러드", "카페라떼"],
            TimeOfDay.AFTERNOON: ["케이크", "와플", "아이스티"],
            TimeOfDay.EVENING: ["파스타", "피자", "샐러드"],
            TimeOfDay.NIGHT: ["디저트", "차", "가벼운 간식"]
        }
        
        # 날씨별 추천 메뉴
        self.weather_recommendations = {
            Weather.HOT: ["아이스티", "오렌지주스", "아이스 아메리카노"],
            Weather.COLD: ["카페라떼", "핫 아메리카노", "그린티라떼"],
            Weather.RAINY: ["따뜻한 음료", "케이크", "와플"],
            Weather.NORMAL: ["아메리카노", "샌드위치", "샐러드"]
        }
        
        logger.info("Recommendation Agent initialized")
    
    async def _ensure_services(self):
        """서비스 초기화 확인"""
        if self.llm_service is None:
            self.llm_service = await get_llm_service()
    
    def _get_time_of_day(self, current_time: Optional[datetime] = None) -> TimeOfDay:
        """
        현재 시간대 판단
        
        Args:
            current_time: 현재 시간 (없으면 현재 시각)
            
        Returns:
            TimeOfDay: 시간대
        """
        if current_time is None:
            current_time = datetime.now()
        
        hour = current_time.hour
        
        if 6 <= hour < 11:
            return TimeOfDay.MORNING
        elif 11 <= hour < 14:
            return TimeOfDay.BRUNCH
        elif 14 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    async def recommend_by_time(
        self,
        current_time: Optional[datetime] = None,
        count: int = 3
    ) -> Recommendation:
        """
        시간대 기반 추천
        
        Args:
            current_time: 현재 시간
            count: 추천 개수
            
        Returns:
            Recommendation: 추천 결과
        """
        time_of_day = self._get_time_of_day(current_time)
        menu_names = self.time_recommendations.get(time_of_day, [])
        
        # 메뉴 아이템 조회
        items = []
        for name in menu_names[:count]:
            # 모든 카테고리에서 검색
            found_items = search_menu(name)
            if found_items:
                items.append(found_items[0])
        
        logger.info(
            "Time-based recommendation",
            time_of_day=time_of_day.value,
            items_count=len(items)
        )
        
        return Recommendation(
            items=items,
            reason=f"{time_of_day.value} 시간대에 인기 있는 메뉴입니다",
            confidence=0.8
        )
    
    async def recommend_by_weather(
        self,
        weather: Weather,
        count: int = 3
    ) -> Recommendation:
        """
        날씨 기반 추천
        
        Args:
            weather: 날씨
            count: 추천 개수
            
        Returns:
            Recommendation: 추천 결과
        """
        menu_names = self.weather_recommendations.get(weather, [])
        
        items = []
        for name in menu_names[:count]:
            found_items = search_menu(name)
            if found_items:
                items.append(found_items[0])
        
        logger.info(
            "Weather-based recommendation",
            weather=weather.value,
            items_count=len(items)
        )
        
        return Recommendation(
            items=items,
            reason=f"{weather.value} 날씨에 어울리는 메뉴입니다",
            confidence=0.75
        )
    
    async def recommend_complementary(
        self,
        order_items: List[Dict[str, Any]],
        count: int = 2
    ) -> Recommendation:
        """
        주문에 어울리는 보완 메뉴 추천
        
        Args:
            order_items: 현재 주문 항목
            count: 추천 개수
            
        Returns:
            Recommendation: 추천 결과
        """
        await self._ensure_services()
        
        try:
            # LLM을 통한 추천
            recommendation_text = await self.llm_service.generate_recommendation(
                order_items,
                {}
            )
            
            # 추천된 메뉴 파싱 (간단화)
            # 실제로는 더 정교한 파싱 필요
            items = await self._parse_recommended_menus(recommendation_text, count)
            
            logger.info(
                "Complementary recommendation generated",
                order_items_count=len(order_items),
                recommended_count=len(items)
            )
            
            return Recommendation(
                items=items,
                reason=recommendation_text,
                confidence=0.85
            )
        
        except Exception as e:
            logger.error(f"Failed to generate complementary recommendation", error=str(e))
            
            # 폴백: 인기 메뉴 추천
            return await self.recommend_popular(count)
    
    async def recommend_popular(
        self,
        count: int = 5,
        category: Optional[MenuCategory] = None
    ) -> Recommendation:
        """
        인기 메뉴 추천
        
        Args:
            count: 추천 개수
            category: 카테고리 필터
            
        Returns:
            Recommendation: 추천 결과
        """
        # 인기 메뉴 조회
        popular_items_data = await self.order_service.get_popular_items(count)
        
        items = []
        for item_data in popular_items_data:
            menu_name = item_data["menu_name"]
            found_items = search_menu(menu_name)
            
            if found_items:
                item = found_items[0]
                # 카테고리 필터
                if category is None or item.category == category:
                    items.append(item)
        
        logger.info(
            "Popular items recommendation",
            count=len(items),
            category=category.value if category else "all"
        )
        
        return Recommendation(
            items=items[:count],
            reason="고객들이 가장 많이 주문한 메뉴입니다",
            confidence=0.9,
            category=category
        )
    
    async def recommend_by_preference(
        self,
        preferences: Dict[str, Any],
        count: int = 3
    ) -> Recommendation:
        """
        고객 선호도 기반 추천
        
        Args:
            preferences: 선호도 정보
            count: 추천 개수
            
        Returns:
            Recommendation: 추천 결과
        """
        items = []
        reason_parts = []
        
        # 선호 카테고리
        if "category" in preferences:
            category = MenuCategory(preferences["category"])
            menu_dict = get_menu_by_category(category)
            items.extend(list(menu_dict.values())[:count])
            reason_parts.append(f"{category.value} 카테고리를 선호하시는군요")
        
        # 가격대
        if "price_range" in preferences:
            min_price, max_price = preferences["price_range"]
            filtered = [
                item for item in items
                if min_price <= item.base_price <= max_price
            ]
            if filtered:
                items = filtered
                reason_parts.append(f"{min_price}-{max_price}원 가격대")
        
        # 키워드
        if "keywords" in preferences:
            for keyword in preferences["keywords"]:
                found = search_menu(keyword)
                items.extend(found[:2])
                reason_parts.append(f"'{keyword}' 관련 메뉴")
        
        # 중복 제거
        unique_items = list({item.name: item for item in items}.values())
        
        reason = "고객님의 선호도에 맞춰 " + ", ".join(reason_parts) + "를 추천드립니다"
        
        logger.info(
            "Preference-based recommendation",
            preferences=preferences,
            items_count=len(unique_items)
        )
        
        return Recommendation(
            items=unique_items[:count],
            reason=reason,
            confidence=0.8
        )
    
    async def recommend_by_category(
        self,
        category: MenuCategory,
        count: int = 3,
        sort_by: str = "popular"
    ) -> Recommendation:
        """
        카테고리별 추천
        
        Args:
            category: 카테고리
            count: 추천 개수
            sort_by: 정렬 기준 (popular, price_low, price_high)
            
        Returns:
            Recommendation: 추천 결과
        """
        menu_dict = get_menu_by_category(category)
        items = list(menu_dict.values())
        
        # 정렬
        if sort_by == "price_low":
            items.sort(key=lambda x: x.base_price)
            reason = f"{category.value} 카테고리의 가성비 좋은 메뉴"
        elif sort_by == "price_high":
            items.sort(key=lambda x: x.base_price, reverse=True)
            reason = f"{category.value} 카테고리의 프리미엄 메뉴"
        else:
            # popular: 인기순 (실제로는 주문 데이터 기반)
            reason = f"{category.value} 카테고리의 인기 메뉴"
        
        logger.info(
            "Category-based recommendation",
            category=category.value,
            sort_by=sort_by,
            items_count=len(items)
        )
        
        return Recommendation(
            items=items[:count],
            reason=reason,
            confidence=0.85,
            category=category
        )
    
    async def recommend_combo(
        self,
        count: int = 3
    ) -> List[Recommendation]:
        """
        조합 추천 (음료 + 디저트 등)
        
        Args:
            count: 조합 개수
            
        Returns:
            List[Recommendation]: 조합 추천 리스트
        """
        combos = []
        
        # 커피 + 디저트 조합
        beverage_dict = get_menu_by_category(MenuCategory.BEVERAGE)
        dessert_dict = get_menu_by_category(MenuCategory.DESSERT)
        
        coffee_items = [item for item in beverage_dict.values() if "커피" in item.name or "라떼" in item.name]
        desserts = list(dessert_dict.values())
        
        if coffee_items and desserts:
            combo_items = [coffee_items[0], desserts[0]]
            combos.append(Recommendation(
                items=combo_items,
                reason="커피와 디저트의 완벽한 조합",
                confidence=0.9,
                category=None
            ))
        
        # 식사 + 음료 조합
        meal_dict = get_menu_by_category(MenuCategory.MEAL)
        meals = list(meal_dict.values())
        
        if meals and beverage_dict:
            combo_items = [meals[0], list(beverage_dict.values())[0]]
            combos.append(Recommendation(
                items=combo_items,
                reason="식사와 함께 즐기기 좋은 음료",
                confidence=0.85,
                category=None
            ))
        
        logger.info(f"Combo recommendations generated", count=len(combos))
        
        return combos[:count]
    
    async def _parse_recommended_menus(
        self,
        recommendation_text: str,
        count: int
    ) -> List[MenuItem]:
        """
        추천 텍스트에서 메뉴 파싱
        
        Args:
            recommendation_text: 추천 텍스트
            count: 개수
            
        Returns:
            List[MenuItem]: 메뉴 아이템 리스트
        """
        # 간단한 파싱: 모든 메뉴 이름 검색
        all_menus = []
        for category in MenuCategory:
            menu_dict = get_menu_by_category(category)
            all_menus.extend(menu_dict.keys())
        
        # 텍스트에서 메뉴 이름 찾기
        found_items = []
        for menu_name in all_menus:
            if menu_name in recommendation_text:
                items = search_menu(menu_name)
                if items:
                    found_items.append(items[0])
        
        return found_items[:count]
    
    async def get_recommendation_stats(self) -> Dict[str, Any]:
        """
        추천 통계
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        popular_items = await self.order_service.get_popular_items(10)
        
        return {
            "popular_items": popular_items,
            "time_of_day": self._get_time_of_day().value,
            "recommendation_types": [
                "time_based",
                "weather_based",
                "complementary",
                "popular",
                "preference_based",
                "category_based",
                "combo"
            ]
        }


# 싱글톤 인스턴스
_recommendation_agent: Optional[RecommendationAgent] = None


def get_recommendation_agent() -> RecommendationAgent:
    """
    추천 에이전트 인스턴스 반환
    
    Returns:
        RecommendationAgent: 추천 에이전트 인스턴스
    """
    global _recommendation_agent
    if _recommendation_agent is None:
        _recommendation_agent = RecommendationAgent()
    return _recommendation_agent
