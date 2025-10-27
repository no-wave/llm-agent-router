"""
메뉴 데이터베이스 모듈
카페의 전체 메뉴 정보를 관리합니다.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class MenuCategory(str, Enum):
    """메뉴 카테고리"""
    BEVERAGE = "음료"
    DESSERT = "디저트"
    MEAL = "식사"


class SizeOption(str, Enum):
    """사이즈 옵션"""
    TALL = "Tall"
    GRANDE = "Grande"
    VENTI = "Venti"


class TemperatureOption(str, Enum):
    """온도 옵션"""
    HOT = "Hot"
    ICE = "Ice"


@dataclass
class MenuItem:
    """메뉴 아이템"""
    name: str
    category: MenuCategory
    base_price: int
    description: str = ""
    available: bool = True
    size_options: List[SizeOption] = field(default_factory=list)
    temperature_options: List[TemperatureOption] = field(default_factory=list)
    extra_options: List[str] = field(default_factory=list)
    
    def get_price(self, size: Optional[SizeOption] = None) -> int:
        """
        사이즈에 따른 가격 계산
        
        Args:
            size: 사이즈 옵션
            
        Returns:
            int: 최종 가격
        """
        price = self.base_price
        
        if size == SizeOption.GRANDE:
            price += 500
        elif size == SizeOption.VENTI:
            price += 1000
            
        return price


# 음료 메뉴
BEVERAGE_MENU = {
    "아메리카노": MenuItem(
        name="아메리카노",
        category=MenuCategory.BEVERAGE,
        base_price=4500,
        description="진한 에스프레소에 물을 더한 클래식 커피",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.HOT, TemperatureOption.ICE],
        extra_options=["샷 추가", "시럽 추가"]
    ),
    "카페라떼": MenuItem(
        name="카페라떼",
        category=MenuCategory.BEVERAGE,
        base_price=5000,
        description="부드러운 우유와 에스프레소의 조화",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.HOT, TemperatureOption.ICE],
        extra_options=["샷 추가", "시럽 추가", "휘핑 추가"]
    ),
    "카푸치노": MenuItem(
        name="카푸치노",
        category=MenuCategory.BEVERAGE,
        base_price=5000,
        description="풍성한 우유 거품이 특징인 이탈리안 커피",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.HOT, TemperatureOption.ICE],
        extra_options=["샷 추가", "시나몬 파우더"]
    ),
    "바닐라라떼": MenuItem(
        name="바닐라라떼",
        category=MenuCategory.BEVERAGE,
        base_price=5500,
        description="달콤한 바닐라 시럽이 들어간 라떼",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.HOT, TemperatureOption.ICE],
        extra_options=["샷 추가", "휘핑 추가"]
    ),
    "카라멜마끼아또": MenuItem(
        name="카라멜마끼아또",
        category=MenuCategory.BEVERAGE,
        base_price=5800,
        description="달콤한 카라멜과 에스프레소의 만남",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.HOT, TemperatureOption.ICE],
        extra_options=["샷 추가", "휘핑 추가", "카라멜 드리즐 추가"]
    ),
    "아이스티": MenuItem(
        name="아이스티",
        category=MenuCategory.BEVERAGE,
        base_price=4000,
        description="상큼한 레몬 아이스티",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.ICE],
        extra_options=["레몬 추가", "민트 추가"]
    ),
    "오렌지주스": MenuItem(
        name="오렌지주스",
        category=MenuCategory.BEVERAGE,
        base_price=5500,
        description="신선한 오렌지로 만든 착즙 주스",
        size_options=[SizeOption.TALL, SizeOption.GRANDE],
        temperature_options=[TemperatureOption.ICE],
        extra_options=[]
    ),
    "그린티라떼": MenuItem(
        name="그린티라떼",
        category=MenuCategory.BEVERAGE,
        base_price=5500,
        description="고소한 녹차와 우유의 조화",
        size_options=[SizeOption.TALL, SizeOption.GRANDE, SizeOption.VENTI],
        temperature_options=[TemperatureOption.HOT, TemperatureOption.ICE],
        extra_options=["휘핑 추가"]
    ),
}

# 디저트 메뉴
DESSERT_MENU = {
    "케이크": MenuItem(
        name="케이크",
        category=MenuCategory.DESSERT,
        base_price=6000,
        description="촉촉한 초콜릿 케이크",
        extra_options=["휘핑 추가"]
    ),
    "치즈케이크": MenuItem(
        name="치즈케이크",
        category=MenuCategory.DESSERT,
        base_price=6500,
        description="부드러운 뉴욕 스타일 치즈케이크",
        extra_options=[]
    ),
    "마카롱": MenuItem(
        name="마카롱",
        category=MenuCategory.DESSERT,
        base_price=3000,
        description="프랑스 전통 마카롱 (5개입)",
        extra_options=[]
    ),
    "쿠키": MenuItem(
        name="쿠키",
        category=MenuCategory.DESSERT,
        base_price=2500,
        description="바삭한 초콜릿칩 쿠키",
        extra_options=[]
    ),
    "와플": MenuItem(
        name="와플",
        category=MenuCategory.DESSERT,
        base_price=7000,
        description="벨기에 스타일 와플",
        extra_options=["아이스크림 추가", "생크림 추가", "메이플시럽 추가"]
    ),
    "타르트": MenuItem(
        name="타르트",
        category=MenuCategory.DESSERT,
        base_price=6500,
        description="신선한 과일 타르트",
        extra_options=[]
    ),
    "브라우니": MenuItem(
        name="브라우니",
        category=MenuCategory.DESSERT,
        base_price=4500,
        description="진한 초콜릿 브라우니",
        extra_options=["아이스크림 추가"]
    ),
    "스콘": MenuItem(
        name="스콘",
        category=MenuCategory.DESSERT,
        base_price=3500,
        description="영국식 스콘 (잼&크림 포함)",
        extra_options=[]
    ),
}

# 식사 메뉴
MEAL_MENU = {
    "샌드위치": MenuItem(
        name="샌드위치",
        category=MenuCategory.MEAL,
        base_price=8000,
        description="신선한 야채와 햄이 들어간 클럽 샌드위치",
        extra_options=["치즈 추가", "베이컨 추가"]
    ),
    "베이글": MenuItem(
        name="베이글",
        category=MenuCategory.MEAL,
        base_price=7000,
        description="크림치즈를 곁들인 베이글",
        extra_options=["연어 추가", "아보카도 추가"]
    ),
    "샐러드": MenuItem(
        name="샐러드",
        category=MenuCategory.MEAL,
        base_price=9000,
        description="신선한 채소와 닭가슴살 샐러드",
        extra_options=["발사믹 드레싱", "요거트 드레싱"]
    ),
    "파스타": MenuItem(
        name="파스타",
        category=MenuCategory.MEAL,
        base_price=12000,
        description="토마토 소스 파스타",
        extra_options=["치즈 추가", "버섯 추가"]
    ),
    "리조또": MenuItem(
        name="리조또",
        category=MenuCategory.MEAL,
        base_price=13000,
        description="크리미한 버섯 리조또",
        extra_options=["치즈 추가", "트러플 오일"]
    ),
    "피자": MenuItem(
        name="피자",
        category=MenuCategory.MEAL,
        base_price=15000,
        description="마르게리타 피자 (1판)",
        extra_options=["치즈 추가", "토핑 추가"]
    ),
    "크로와상": MenuItem(
        name="크로와상",
        category=MenuCategory.MEAL,
        base_price=4000,
        description="버터 크로와상",
        extra_options=[]
    ),
    "프렌치토스트": MenuItem(
        name="프렌치토스트",
        category=MenuCategory.MEAL,
        base_price=8500,
        description="시나몬 프렌치토스트",
        extra_options=["아이스크림 추가", "메이플시럽 추가"]
    ),
}

# 통합 메뉴 데이터베이스
MENU_DATABASE: Dict[MenuCategory, Dict[str, MenuItem]] = {
    MenuCategory.BEVERAGE: BEVERAGE_MENU,
    MenuCategory.DESSERT: DESSERT_MENU,
    MenuCategory.MEAL: MEAL_MENU,
}


def get_menu_by_category(category: MenuCategory) -> Dict[str, MenuItem]:
    """
    카테고리별 메뉴 조회
    
    Args:
        category: 메뉴 카테고리
        
    Returns:
        Dict[str, MenuItem]: 메뉴 딕셔너리
    """
    return MENU_DATABASE.get(category, {})


def get_menu_item(name: str, category: Optional[MenuCategory] = None) -> Optional[MenuItem]:
    """
    메뉴 아이템 조회
    
    Args:
        name: 메뉴 이름
        category: 메뉴 카테고리 (선택)
        
    Returns:
        Optional[MenuItem]: 메뉴 아이템 또는 None
    """
    if category:
        return MENU_DATABASE.get(category, {}).get(name)
    
    # 전체 카테고리에서 검색
    for cat_menu in MENU_DATABASE.values():
        if name in cat_menu:
            return cat_menu[name]
    
    return None


def get_all_menu_names() -> List[str]:
    """
    전체 메뉴 이름 목록 반환
    
    Returns:
        List[str]: 메뉴 이름 리스트
    """
    names = []
    for cat_menu in MENU_DATABASE.values():
        names.extend(cat_menu.keys())
    return names


def search_menu(keyword: str) -> List[MenuItem]:
    """
    키워드로 메뉴 검색
    
    Args:
        keyword: 검색 키워드
        
    Returns:
        List[MenuItem]: 검색된 메뉴 리스트
    """
    results = []
    keyword_lower = keyword.lower()
    
    for cat_menu in MENU_DATABASE.values():
        for menu_item in cat_menu.values():
            if (keyword_lower in menu_item.name.lower() or 
                keyword_lower in menu_item.description.lower()):
                results.append(menu_item)
    
    return results
