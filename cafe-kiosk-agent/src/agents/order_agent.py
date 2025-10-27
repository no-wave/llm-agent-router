"""
주문 처리 에이전트 모듈
주문의 전체 프로세스를 관리합니다.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config.menu_database import MenuCategory, get_menu_by_category
from src.routers import (
    get_category_router,
    get_model_router,
    get_serving_router
)
from src.services import (
    get_llm_service,
    get_order_service,
    Order,
    OrderStatus
)
from src.utils import (
    get_logger,
    LogContext,
    OrderValidator,
    TextNormalizer,
    InputSanitizer
)


logger = get_logger(__name__)


@dataclass
class OrderProcessResult:
    """주문 처리 결과"""
    success: bool
    order: Optional[Order] = None
    message: str = ""
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "order": self.order.to_dict() if self.order else None,
            "message": self.message,
            "errors": self.errors
        }


class OrderAgent:
    """주문 처리 에이전트"""
    
    def __init__(self):
        """초기화"""
        self.category_router = get_category_router()
        self.model_router = get_model_router()
        self.serving_router = get_serving_router()
        self.llm_service = None
        self.order_service = get_order_service()
        
        logger.info("Order Agent initialized")
    
    async def _ensure_services(self):
        """서비스 초기화 확인"""
        if self.llm_service is None:
            self.llm_service = await get_llm_service()
    
    async def process_order(
        self,
        order_text: str,
        customer_notes: str = ""
    ) -> OrderProcessResult:
        """
        주문 처리 메인 프로세스
        
        Args:
            order_text: 주문 텍스트
            customer_notes: 고객 메모
            
        Returns:
            OrderProcessResult: 주문 처리 결과
        """
        async with LogContext(
            logger,
            "process_order",
            order_text=order_text[:100]
        ):
            try:
                # 1. 입력 검증 및 정규화
                validated = await self._validate_and_sanitize(order_text)
                if not validated["success"]:
                    return OrderProcessResult(
                        success=False,
                        message=validated["message"],
                        errors=validated.get("errors", [])
                    )
                
                clean_text = validated["text"]
                
                # 2. 카테고리 라우팅
                category_decision = await self.category_router.route(clean_text)
                
                logger.info(
                    "Order routed to category",
                    category=category_decision.category.value,
                    confidence=category_decision.confidence
                )
                
                # 3. 메뉴 항목 추출
                items = await self._extract_order_items(
                    clean_text,
                    category_decision.category
                )
                
                if not items:
                    return OrderProcessResult(
                        success=False,
                        message="주문 항목을 찾을 수 없습니다. 다시 시도해주세요.",
                        errors=["no_items_extracted"]
                    )
                
                # 4. 항목 검증
                validation_result = OrderValidator.validate_order_items(items)
                if not validation_result.is_valid:
                    return OrderProcessResult(
                        success=False,
                        message=validation_result.message,
                        errors=validation_result.errors
                    )
                
                # 5. 주문 생성
                order = await self.order_service.create_order_from_items(
                    items_data=items,
                    category=category_decision.category,
                    customer_notes=customer_notes
                )
                
                # 6. 주문 상태 업데이트
                await self.order_service.update_order_status(
                    order.order_id,
                    OrderStatus.CONFIRMED
                )
                
                logger.info(
                    "Order processed successfully",
                    order_id=order.order_id,
                    items_count=len(items),
                    total_amount=order.total_amount
                )
                
                return OrderProcessResult(
                    success=True,
                    order=order,
                    message=f"주문이 접수되었습니다. (주문번호: {order.order_id})"
                )
            
            except Exception as e:
                logger.log_error_with_traceback(
                    "Failed to process order",
                    e
                )
                
                return OrderProcessResult(
                    success=False,
                    message="주문 처리 중 오류가 발생했습니다.",
                    errors=[str(e)]
                )
    
    async def _validate_and_sanitize(
        self,
        order_text: str
    ) -> Dict[str, Any]:
        """
        입력 검증 및 살균
        
        Args:
            order_text: 주문 텍스트
            
        Returns:
            Dict[str, Any]: 검증 결과
        """
        # 기본 검증
        validation = OrderValidator.validate_order_text(order_text)
        if not validation.is_valid:
            return {
                "success": False,
                "message": validation.message,
                "errors": validation.errors
            }
        
        # 살균
        clean_text = InputSanitizer.sanitize_text(order_text)
        
        # 안전한 문자 확인
        if not InputSanitizer.validate_safe_characters(clean_text):
            return {
                "success": False,
                "message": "허용되지 않은 문자가 포함되어 있습니다.",
                "errors": ["unsafe_characters"]
            }
        
        # 정규화
        normalized_text = TextNormalizer.normalize_whitespace(clean_text)
        normalized_text = TextNormalizer.normalize_numbers(normalized_text)
        
        return {
            "success": True,
            "text": normalized_text
        }
    
    async def _extract_order_items(
        self,
        order_text: str,
        category: MenuCategory
    ) -> List[Dict[str, Any]]:
        """
        주문 항목 추출
        
        Args:
            order_text: 주문 텍스트
            category: 카테고리
            
        Returns:
            List[Dict[str, Any]]: 추출된 항목 리스트
        """
        await self._ensure_services()
        
        # 해당 카테고리의 사용 가능한 메뉴 목록
        available_menus = await self.category_router.get_available_menus(category)
        
        # LLM을 통한 항목 추출
        items = await self.llm_service.extract_order_items(
            order_text,
            category.value,
            available_menus
        )
        
        # 카테고리 검증
        validated_items = await self.category_router.validate_category_items(
            category,
            items
        )
        
        return validated_items
    
    async def process_batch_orders(
        self,
        order_texts: List[str]
    ) -> List[OrderProcessResult]:
        """
        여러 주문을 배치로 처리
        
        Args:
            order_texts: 주문 텍스트 리스트
            
        Returns:
            List[OrderProcessResult]: 처리 결과 리스트
        """
        async with LogContext(
            logger,
            "process_batch_orders",
            count=len(order_texts)
        ):
            tasks = [self.process_order(text) for text in order_texts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to process order {i}",
                        error=str(result)
                    )
                    processed_results.append(OrderProcessResult(
                        success=False,
                        message="주문 처리 실패",
                        errors=[str(result)]
                    ))
                else:
                    processed_results.append(result)
            
            success_count = sum(1 for r in processed_results if r.success)
            logger.info(
                f"Batch orders processed",
                total=len(order_texts),
                success=success_count,
                failed=len(order_texts) - success_count
            )
            
            return processed_results
    
    async def modify_order(
        self,
        order_id: str,
        modifications: Dict[str, Any]
    ) -> OrderProcessResult:
        """
        주문 수정
        
        Args:
            order_id: 주문 ID
            modifications: 수정 내용
            
        Returns:
            OrderProcessResult: 처리 결과
        """
        try:
            order = await self.order_service.get_order(order_id)
            
            if order is None:
                return OrderProcessResult(
                    success=False,
                    message=f"주문을 찾을 수 없습니다. (ID: {order_id})",
                    errors=["order_not_found"]
                )
            
            # 수정 처리 (예: 항목 추가/제거)
            if "add_items" in modifications:
                for item_data in modifications["add_items"]:
                    # 항목 추가 로직
                    pass
            
            if "remove_items" in modifications:
                for menu_name in modifications["remove_items"]:
                    order.remove_item(menu_name)
            
            logger.info(
                "Order modified",
                order_id=order_id,
                modifications=modifications
            )
            
            return OrderProcessResult(
                success=True,
                order=order,
                message="주문이 수정되었습니다."
            )
        
        except Exception as e:
            logger.log_error_with_traceback("Failed to modify order", e)
            return OrderProcessResult(
                success=False,
                message="주문 수정 중 오류가 발생했습니다.",
                errors=[str(e)]
            )
    
    async def cancel_order(self, order_id: str) -> OrderProcessResult:
        """
        주문 취소
        
        Args:
            order_id: 주문 ID
            
        Returns:
            OrderProcessResult: 처리 결과
        """
        try:
            success = await self.order_service.cancel_order(order_id)
            
            if success:
                order = await self.order_service.get_order(order_id)
                return OrderProcessResult(
                    success=True,
                    order=order,
                    message="주문이 취소되었습니다."
                )
            else:
                return OrderProcessResult(
                    success=False,
                    message=f"주문을 찾을 수 없습니다. (ID: {order_id})",
                    errors=["order_not_found"]
                )
        
        except Exception as e:
            logger.log_error_with_traceback("Failed to cancel order", e)
            return OrderProcessResult(
                success=False,
                message="주문 취소 중 오류가 발생했습니다.",
                errors=[str(e)]
            )
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        주문 상태 조회
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Dict[str, Any]: 주문 상태 정보
        """
        order = await self.order_service.get_order(order_id)
        
        if order is None:
            return {
                "found": False,
                "message": "주문을 찾을 수 없습니다."
            }
        
        return {
            "found": True,
            "order_id": order.order_id,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "items_count": len(order.items),
            "total_amount": order.total_amount,
            "final_amount": order.final_amount
        }
    
    async def get_active_orders(self) -> List[Dict[str, Any]]:
        """
        활성 주문 목록 조회
        
        Returns:
            List[Dict[str, Any]]: 주문 목록
        """
        orders = await self.order_service.get_active_orders()
        return [order.to_dict() for order in orders]
    
    async def print_receipt(self, order_id: str) -> Optional[str]:
        """
        영수증 출력
        
        Args:
            order_id: 주문 ID
            
        Returns:
            Optional[str]: 영수증 텍스트
        """
        order = await self.order_service.get_order(order_id)
        
        if order is None:
            logger.warning(f"Order not found for receipt: {order_id}")
            return None
        
        receipt = order.generate_receipt()
        logger.info(f"Receipt generated", order_id=order_id)
        
        return receipt
    
    async def process_natural_language_query(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        자연어 질의 처리
        
        Args:
            query: 질의 텍스트
            
        Returns:
            Dict[str, Any]: 응답
        """
        await self._ensure_services()
        
        # 모델 선택
        model_selection = await self.model_router.route(query)
        
        # LLM 호출
        response = await self.llm_service.chat_completion(
            messages=[{"role": "user", "content": query}],
            model_type=model_selection.model_type,
            model_name=model_selection.model_name,
        )
        
        return {
            "query": query,
            "response": response,
            "model_used": model_selection.model_name,
            "complexity": model_selection.complexity.value
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        에이전트 통계 정보
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            "category_stats": self.category_router.get_category_stats(),
            "model_stats": self.model_router.get_selection_stats(),
            "serving_stats": self.serving_router.get_serving_stats(),
            "daily_revenue": await self.order_service.calculate_daily_revenue(),
            "popular_items": await self.order_service.get_popular_items()
        }


# 싱글톤 인스턴스
_order_agent: Optional[OrderAgent] = None


def get_order_agent() -> OrderAgent:
    """
    주문 에이전트 인스턴스 반환
    
    Returns:
        OrderAgent: 주문 에이전트 인스턴스
    """
    global _order_agent
    if _order_agent is None:
        _order_agent = OrderAgent()
    return _order_agent