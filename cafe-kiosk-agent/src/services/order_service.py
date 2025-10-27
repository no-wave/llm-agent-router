"""
주문 관리 서비스 모듈
주문 생성, 관리, 히스토리를 담당합니다.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from config.menu_database import (
    get_menu_item,
    MenuItem,
    MenuCategory,
    SizeOption,
)
from config.settings import settings
from src.utils.logger import get_logger
from src.utils.validators import OrderValidator


logger = get_logger(__name__)


class OrderStatus(str, Enum):
    """주문 상태"""
    PENDING = "pending"           # 대기중
    PROCESSING = "processing"     # 처리중
    CONFIRMED = "confirmed"       # 확인됨
    PREPARING = "preparing"       # 준비중
    READY = "ready"               # 준비완료
    COMPLETED = "completed"       # 완료
    CANCELLED = "cancelled"       # 취소됨


@dataclass
class OrderItem:
    """주문 항목"""
    menu_name: str
    quantity: int
    category: MenuCategory
    base_price: int
    size: Optional[SizeOption] = None
    options: List[str] = field(default_factory=list)
    subtotal: int = 0
    
    def __post_init__(self):
        """주문 항목 초기화 후 처리"""
        self.calculate_subtotal()
    
    def calculate_subtotal(self):
        """소계 계산"""
        menu_item = get_menu_item(self.menu_name)
        if menu_item:
            price = menu_item.get_price(self.size)
            
            # 옵션 추가 비용 (간단화)
            option_cost = len(self.options) * 500
            
            self.subtotal = (price + option_cost) * self.quantity
        else:
            self.subtotal = self.base_price * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "menu_name": self.menu_name,
            "quantity": self.quantity,
            "category": self.category.value,
            "size": self.size.value if self.size else None,
            "options": self.options,
            "base_price": self.base_price,
            "subtotal": self.subtotal
        }


@dataclass
class Order:
    """주문"""
    order_id: str
    items: List[OrderItem]
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    customer_notes: str = ""
    total_amount: int = 0
    tax_amount: int = 0
    final_amount: int = 0
    
    def __post_init__(self):
        """주문 초기화 후 처리"""
        self.calculate_amounts()
    
    def calculate_amounts(self):
        """금액 계산"""
        # 총 금액
        self.total_amount = sum(item.subtotal for item in self.items)
        
        # 세금
        if settings.tax_rate > 0:
            self.tax_amount = int(self.total_amount * settings.tax_rate)
        else:
            self.tax_amount = 0
        
        # 최종 금액
        self.final_amount = self.total_amount + self.tax_amount
    
    def update_status(self, new_status: OrderStatus):
        """
        주문 상태 업데이트
        
        Args:
            new_status: 새로운 상태
        """
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()
        
        logger.info(
            f"Order status updated",
            order_id=self.order_id,
            old_status=old_status.value,
            new_status=new_status.value
        )
    
    def add_item(self, item: OrderItem):
        """
        주문 항목 추가
        
        Args:
            item: 주문 항목
        """
        self.items.append(item)
        self.calculate_amounts()
        self.updated_at = datetime.now()
        
        logger.info(
            f"Item added to order",
            order_id=self.order_id,
            menu_name=item.menu_name,
            quantity=item.quantity
        )
    
    def remove_item(self, menu_name: str) -> bool:
        """
        주문 항목 제거
        
        Args:
            menu_name: 제거할 메뉴 이름
            
        Returns:
            bool: 제거 성공 여부
        """
        original_count = len(self.items)
        self.items = [item for item in self.items if item.menu_name != menu_name]
        
        if len(self.items) < original_count:
            self.calculate_amounts()
            self.updated_at = datetime.now()
            logger.info(
                f"Item removed from order",
                order_id=self.order_id,
                menu_name=menu_name
            )
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "order_id": self.order_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
            "customer_notes": self.customer_notes,
            "total_amount": self.total_amount,
            "tax_amount": self.tax_amount,
            "final_amount": self.final_amount
        }
    
    def generate_receipt(self) -> str:
        """
        영수증 생성
        
        Returns:
            str: 영수증 텍스트
        """
        receipt_lines = [
            "=" * 50,
            "            카페 키오스크",
            "=" * 50,
            f"주문번호: {self.order_id}",
            f"주문시간: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"상태: {self.status.value}",
            "-" * 50,
            "주문 내역:",
            ""
        ]
        
        for item in self.items:
            item_line = f"  {item.menu_name} x {item.quantity}"
            if item.size:
                item_line += f" ({item.size.value})"
            item_line += f" ... {item.subtotal:,}원"
            receipt_lines.append(item_line)
            
            if item.options:
                options_line = f"    옵션: {', '.join(item.options)}"
                receipt_lines.append(options_line)
        
        receipt_lines.extend([
            "",
            "-" * 50,
            f"소계:                    {self.total_amount:,}원",
            f"세금 ({int(settings.tax_rate * 100)}%):              {self.tax_amount:,}원",
            "=" * 50,
            f"총 결제 금액:             {self.final_amount:,}원",
            "=" * 50,
            "",
            "감사합니다!",
            "=" * 50
        ])
        
        return "\n".join(receipt_lines)


class OrderService:
    """주문 관리 서비스"""
    
    def __init__(self):
        """초기화"""
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        logger.info("Order Service initialized")
    
    def generate_order_id(self) -> str:
        """
        주문 ID 생성
        
        Returns:
            str: 주문 ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"ORD-{timestamp}-{unique_id}"
    
    async def create_order_from_items(
        self,
        items_data: List[Dict[str, Any]],
        category: MenuCategory,
        customer_notes: str = ""
    ) -> Order:
        """
        주문 항목 데이터로부터 주문 생성
        
        Args:
            items_data: 주문 항목 데이터 리스트
            category: 메뉴 카테고리
            customer_notes: 고객 메모
            
        Returns:
            Order: 생성된 주문
        """
        # 주문 ID 생성
        order_id = self.generate_order_id()
        
        # 주문 항목 생성
        order_items = []
        
        for item_data in items_data:
            menu_name = item_data.get("menu")
            quantity = item_data.get("quantity", 1)
            
            # 메뉴 아이템 조회
            menu_item = get_menu_item(menu_name, category)
            
            if menu_item is None:
                logger.warning(
                    f"Menu item not found",
                    menu_name=menu_name
                )
                continue
            
            # 사이즈 파싱
            size = None
            if "size" in item_data and item_data["size"]:
                try:
                    size = SizeOption(item_data["size"])
                except ValueError:
                    logger.warning(f"Invalid size: {item_data['size']}")
            
            
            # 옵션
            options = item_data.get("options", [])
            
            # 주문 항목 생성
            order_item = OrderItem(
                menu_name=menu_name,
                quantity=quantity,
                category=category,
                base_price=menu_item.base_price,
                size=size,
                options=options
            )
            
            order_items.append(order_item)
        
        # 주문 생성
        order = Order(
            order_id=order_id,
            items=order_items,
            customer_notes=customer_notes
        )
        
        # 주문 저장
        self.orders[order_id] = order
        
        logger.log_order(
            order_id=order_id,
            status="created",
            details={
                "items_count": len(order_items),
                "total_amount": order.total_amount
            }
        )
        
        return order
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        주문 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Optional[Order]: 주문 객체
        """
        return self.orders.get(order_id)
    
    async def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus
    ) -> bool:
        """
        주문 상태 업데이트
        
        Args:
            order_id: 주문 ID
            new_status: 새로운 상태
            
        Returns:
            bool: 업데이트 성공 여부
        """
        order = await self.get_order(order_id)
        
        if order is None:
            logger.warning(f"Order not found for status update: {order_id}")
            return False
        
        order.update_status(new_status)
        
        # 완료된 주문은 히스토리로 이동
        if new_status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
            self.order_history.append(order)
            del self.orders[order_id]
        
        return True
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소
        
        Args:
            order_id: 주문 ID
            
        Returns:
            bool: 취소 성공 여부
        """
        return await self.update_order_status(order_id, OrderStatus.CANCELLED)
    
    async def get_active_orders(self) -> List[Order]:
        """
        활성 주문 목록 조회
        
        Returns:
            List[Order]: 활성 주문 리스트
        """
        return list(self.orders.values())
    
    async def get_order_history(
        self,
        limit: int = 50
    ) -> List[Order]:
        """
        주문 히스토리 조회
        
        Args:
            limit: 조회 개수 제한
            
        Returns:
            List[Order]: 주문 히스토리
        """
        return self.order_history[-limit:]
    
    async def calculate_daily_revenue(self) -> Dict[str, Any]:
        """
        일일 매출 계산
        
        Returns:
            Dict[str, Any]: 매출 정보
        """
        today = datetime.now().date()
        
        # 오늘의 완료된 주문
        today_orders = [
            order for order in self.order_history
            if order.created_at.date() == today
            and order.status == OrderStatus.COMPLETED
        ]
        
        total_revenue = sum(order.final_amount for order in today_orders)
        total_orders = len(today_orders)
        
        # 카테고리별 매출
        category_revenue = {}
        for order in today_orders:
            for item in order.items:
                cat = item.category.value
                if cat not in category_revenue:
                    category_revenue[cat] = 0
                category_revenue[cat] += item.subtotal
        
        return {
            "date": today.isoformat(),
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "average_order_value": total_revenue // total_orders if total_orders > 0 else 0,
            "category_revenue": category_revenue
        }
    
    async def get_popular_items(
        self,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        인기 메뉴 조회
        
        Args:
            top_n: 상위 N개
            
        Returns:
            List[Dict[str, Any]]: 인기 메뉴 리스트
        """
        item_counts = {}
        
        for order in self.order_history:
            if order.status == OrderStatus.COMPLETED:
                for item in order.items:
                    menu_name = item.menu_name
                    if menu_name not in item_counts:
                        item_counts[menu_name] = 0
                    item_counts[menu_name] += item.quantity
        
        # 정렬
        sorted_items = sorted(
            item_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return [
            {"menu_name": name, "order_count": count}
            for name, count in sorted_items
        ]
    
    def clear_old_history(self, days: int = 30):
        """
        오래된 히스토리 삭제
        
        Args:
            days: 보관 기간 (일)
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        original_count = len(self.order_history)
        self.order_history = [
            order for order in self.order_history
            if order.created_at > cutoff_date
        ]
        
        deleted_count = original_count - len(self.order_history)
        
        if deleted_count > 0:
            logger.info(
                f"Cleared old order history",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date.isoformat()
            )


# 싱글톤 인스턴스
_order_service: Optional[OrderService] = None


def get_order_service() -> OrderService:
    """
    주문 서비스 인스턴스 반환
    
    Returns:
        OrderService: 주문 서비스 인스턴스
    """
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service
