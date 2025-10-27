"""
카페 키오스크 에이전트 메인 실행 파일
"""

import asyncio
import sys
from typing import Optional
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.agents import get_order_agent, get_recommendation_agent
from src.services import get_llm_service
from src.utils import get_main_logger, LogContext


logger = get_main_logger()


class KioskInterface:
    """키오스크 인터페이스"""
    
    def __init__(self):
        """초기화"""
        self.order_agent = get_order_agent()
        self.recommendation_agent = get_recommendation_agent()
        self.running = True
        
        logger.info("Kiosk Interface initialized")
    
    async def start(self):
        """키오스크 시작"""
        logger.info("Starting Cafe Kiosk Agent System")
        
        # 서비스 초기화
        await self._initialize_services()
        
        # 환영 메시지
        self._print_welcome()
        
        # 메인 루프
        await self._main_loop()
    
    async def _initialize_services(self):
        """서비스 초기화"""
        async with LogContext(logger, "initialize_services"):
            # LLM 서비스 초기화
            llm_service = await get_llm_service()
            
            # 로컬 모델 가용성 확인
            local_available = await llm_service.check_local_model_availability()
            
            logger.info(
                "Services initialized",
                local_model_available=local_available,
                model_strategy=settings.model_strategy
            )
    
    def _print_welcome(self):
        """환영 메시지 출력"""
        print("\n" + "=" * 60)
        print("          🎉 카페 키오스크 에이전트에 오신 것을 환영합니다! 🎉")
        print("=" * 60)
        print("\n📋 사용 가능한 명령어:")
        print("  • 주문하기: 메뉴를 자연어로 주문 (예: '아메리카노 2잔 주세요')")
        print("  • 추천: 추천 메뉴 보기")
        print("  • 메뉴: 전체 메뉴 보기")
        print("  • 주문확인: 현재 주문 상태 확인")
        print("  • 통계: 시스템 통계 보기")
        print("  • 도움말: 명령어 도움말")
        print("  • 종료: 프로그램 종료")
        print("\n💡 자연어로 편하게 주문하세요!")
        print("=" * 60 + "\n")
    
    async def _main_loop(self):
        """메인 루프"""
        while self.running:
            try:
                # 사용자 입력 (UTF-8 인코딩 처리)
                try:
                    user_input = input("\n👤 고객님: ").strip()
                except UnicodeDecodeError:
                    # Windows 콘솔에서 발생할 수 있는 인코딩 문제 처리
                    import sys
                    sys.stdin.reconfigure(encoding='utf-8')
                    user_input = input("\n👤 고객님: ").strip()
                
                if not user_input:
                    continue
                
                # 명령어 처리
                await self._process_input(user_input)
            
            except KeyboardInterrupt:
                print("\n\n프로그램을 종료합니다...")
                self.running = False
            
            except UnicodeDecodeError as e:
                logger.error(f"Unicode encoding error", error=str(e))
                print(f"\n❌ 인코딩 오류가 발생했습니다. UTF-8 인코딩을 사용해주세요.")
            
            except Exception as e:
                logger.error(f"Error in main loop", error=str(e))
                print(f"\n❌ 오류가 발생했습니다: {str(e)}")
    
    async def _process_input(self, user_input: str):
        """
        사용자 입력 처리
        
        Args:
            user_input: 사용자 입력
        """
        command = user_input.lower()
        
        # 명령어 매핑
        if command in ["종료", "exit", "quit", "q"]:
            await self._handle_exit()
        
        elif command in ["도움말", "help", "h"]:
            self._print_welcome()
        
        elif command in ["메뉴", "menu", "m"]:
            await self._handle_menu()
        
        elif command in ["추천", "recommend", "r"] or self._is_recommendation_request(user_input):
            await self._handle_recommendation(user_input)
        
        elif command in ["주문확인", "orders", "o"]:
            await self._handle_check_orders()
        
        elif command in ["통계", "stats", "s"]:
            await self._handle_statistics()
        
        else:
            # 주문으로 처리
            await self._handle_order(user_input)
    
    def _is_recommendation_request(self, text: str) -> bool:
        """
        추천 요청인지 판단
        
        Args:
            text: 사용자 입력
            
        Returns:
            bool: 추천 요청 여부
        """
        recommendation_keywords = [
            "추천", "recommend", "추천해", "추천해줘", "추천해주세요",
            "뭐가 좋아", "뭐 먹을까", "뭘 먹지", "고민",
            "인기", "popular", "베스트", "best",
            "메뉴 보여", "메뉴 알려"
        ]
        
        text_lower = text.lower()
        
        # 추천 키워드가 있고 수량이 없으면 추천 요청으로 판단
        has_recommendation_keyword = any(keyword in text_lower for keyword in recommendation_keywords)
        has_quantity = any(str(i) in text for i in range(1, 100)) or any(
            word in text_lower for word in ["잔", "개", "인분", "조각", "판"]
        )
        
        return has_recommendation_keyword and not has_quantity
    
    async def _handle_order(self, order_text: str):
        """
        주문 처리
        
        Args:
            order_text: 주문 텍스트
        """
        print("\n🔄 주문을 처리하고 있습니다...\n")
        
        async with LogContext(logger, "handle_order", order_text=order_text[:50]):
            result = await self.order_agent.process_order(order_text)
            
            if result.success:
                print("✅ " + result.message + "\n")
                
                # 영수증 출력
                if result.order:
                    receipt = result.order.generate_receipt()
                    print(receipt)
                    
                    # 추천 메뉴 제안
                    if settings.enable_recommendations:
                        await self._suggest_complementary(result.order.items)
            
            else:
                print("❌ " + result.message)
                if result.errors:
                    print("\n오류 상세:")
                    for error in result.errors:
                        print(f"  • {error}")
    
    async def _handle_menu(self):
        """메뉴 보기"""
        from config.menu_database import MENU_DATABASE
        
        print("\n" + "=" * 60)
        print("                    📖 전체 메뉴")
        print("=" * 60 + "\n")
        
        for category, menu_dict in MENU_DATABASE.items():
            print(f"\n【 {category.value} 】")
            print("-" * 40)
            
            for name, item in menu_dict.items():
                price_str = f"{item.base_price:,}원"
                status = "✓" if item.available else "✗ 품절"
                print(f"  {name:15s} {price_str:>10s}  [{status}]")
                if item.description:
                    print(f"    └─ {item.description}")
        
        print("\n" + "=" * 60 + "\n")
    
    async def _handle_recommendation(self, user_input: str = ""):
        """
        추천 메뉴
        
        Args:
            user_input: 사용자 입력 (카테고리 추출용)
        """
        print("\n🎯 추천 메뉴를 준비하고 있습니다...\n")
        
        print("=" * 60)
        print("                  ⭐ 추천 메뉴")
        print("=" * 60 + "\n")
        
        # 카테고리 필터링 확인
        from config.menu_database import MenuCategory
        
        category_filter = None
        if user_input:
            user_lower = user_input.lower()
            if "음료" in user_lower or "커피" in user_lower or "beverage" in user_lower:
                category_filter = MenuCategory.BEVERAGE
                print("☕ 음료 메뉴 추천\n")
            elif "디저트" in user_lower or "dessert" in user_lower:
                category_filter = MenuCategory.DESSERT
                print("🍰 디저트 메뉴 추천\n")
            elif "식사" in user_lower or "meal" in user_lower:
                category_filter = MenuCategory.MEAL
                print("🍽️ 식사 메뉴 추천\n")
        
        # 시간대별 추천
        time_rec = await self.recommendation_agent.recommend_by_time(count=3)
        if category_filter is None or any(item.category == category_filter for item in time_rec.items):
            print(f"⏰ 시간대 추천: {time_rec.reason}")
            for item in time_rec.items:
                if category_filter is None or item.category == category_filter:
                    print(f"  • {item.name} - {item.base_price:,}원")
                    if item.description:
                        print(f"    └─ {item.description}")
            print()
        
        # 카테고리별 추천
        if category_filter:
            cat_rec = await self.recommendation_agent.recommend_by_category(
                category_filter,
                count=5,
                sort_by="popular"
            )
            print(f"🔥 {cat_rec.reason}")
            for item in cat_rec.items:
                print(f"  • {item.name} - {item.base_price:,}원")
                if item.description:
                    print(f"    └─ {item.description}")
            print()
        else:
            # 전체 인기 메뉴
            popular_rec = await self.recommendation_agent.recommend_popular(count=5)
            print(f"🔥 {popular_rec.reason}")
            for item in popular_rec.items:
                print(f"  • {item.name} ({item.category.value}) - {item.base_price:,}원")
            print()
            
            # 조합 추천
            combos = await self.recommendation_agent.recommend_combo(count=2)
            if combos:
                print("🍽️ 조합 추천:")
                for i, combo in enumerate(combos, 1):
                    items_str = " + ".join([item.name for item in combo.items])
                    total_price = sum(item.base_price for item in combo.items)
                    print(f"  {i}. {items_str} ({total_price:,}원)")
                    print(f"     └─ {combo.reason}")
        
        print("\n" + "=" * 60 + "\n")
        print("💡 원하시는 메뉴를 말씀해주시면 주문해드리겠습니다!")
    
    async def _suggest_complementary(self, order_items):
        """
        보완 메뉴 제안
        
        Args:
            order_items: 주문 항목
        """
        print("\n💡 함께 주문하시면 좋을 메뉴:")
        
        items_data = [
            {"menu": item.menu_name, "quantity": item.quantity}
            for item in order_items
        ]
        
        rec = await self.recommendation_agent.recommend_complementary(
            items_data,
            count=2
        )
        
        for item in rec.items:
            print(f"  • {item.name} ({item.base_price:,}원)")
    
    async def _handle_check_orders(self):
        """주문 확인"""
        print("\n📋 현재 주문 상태를 확인합니다...\n")
        
        orders = await self.order_agent.get_active_orders()
        
        if not orders:
            print("현재 진행 중인 주문이 없습니다.\n")
            return
        
        print("=" * 60)
        print("                 현재 진행 중인 주문")
        print("=" * 60 + "\n")
        
        for order_data in orders:
            print(f"주문번호: {order_data['order_id']}")
            print(f"상태: {order_data['status']}")
            print(f"주문 시간: {order_data['created_at']}")
            print(f"항목 수: {order_data['items_count']}개")
            print(f"결제 금액: {order_data['final_amount']:,}원")
            print("-" * 60)
        
        print()
    
    async def _handle_statistics(self):
        """통계 보기"""
        print("\n📊 시스템 통계를 불러오고 있습니다...\n")
        
        stats = await self.order_agent.get_statistics()
        
        print("=" * 60)
        print("                   시스템 통계")
        print("=" * 60 + "\n")
        
        # 일일 매출
        revenue = stats.get("daily_revenue", {})
        print(f"📅 오늘의 매출")
        print(f"  총 매출: {revenue.get('total_revenue', 0):,}원")
        print(f"  주문 건수: {revenue.get('total_orders', 0)}건")
        print(f"  평균 주문액: {revenue.get('average_order_value', 0):,}원")
        print()
        
        # 인기 메뉴
        popular = stats.get("popular_items", [])
        if popular:
            print("🏆 인기 메뉴 TOP 5")
            for i, item in enumerate(popular[:5], 1):
                print(f"  {i}. {item['menu_name']} - {item['order_count']}회 주문")
            print()
        
        # 카테고리 통계
        cat_stats = stats.get("category_stats", {})
        if cat_stats:
            print("📊 카테고리별 메뉴 수")
            for category, count in cat_stats.items():
                print(f"  {category}: {count}개")
            print()
        
        # 모델 사용 통계
        model_stats = stats.get("model_stats", {})
        if model_stats.get("total_selections", 0) > 0:
            print("🤖 AI 모델 사용 통계")
            print(f"  총 사용 횟수: {model_stats['total_selections']}회")
            print(f"  평균 비용: {model_stats.get('average_cost', 0):.2f}")
            
            usage = model_stats.get("model_usage", {})
            if usage:
                print("  모델별 사용:")
                for model, count in usage.items():
                    print(f"    • {model}: {count}회")
            print()
        
        print("=" * 60 + "\n")
    
    async def _handle_exit(self):
        """종료 처리"""
        print("\n👋 이용해 주셔서 감사합니다!")
        print("안녕히 가세요!\n")
        
        self.running = False
        
        # 리소스 정리
        llm_service = await get_llm_service()
        await llm_service.close()
        
        logger.info("Kiosk system shutdown")


async def main():
    """메인 함수"""
    try:
        # 키오스크 인터페이스 시작
        kiosk = KioskInterface()
        await kiosk.start()
    
    except Exception as e:
        logger.error(f"Fatal error in main", error=str(e))
        print(f"\n❌ 치명적 오류: {str(e)}")
        sys.exit(1)


def run():
    """실행 함수"""
    # 콘솔 인코딩 설정 (Windows 환경 대응)
    import sys
    import io
    
    # Windows에서 UTF-8 출력 설정
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
            sys.stdin.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python 3.6 이하 버전 대응
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    
    # 환경 확인
    if not settings.openai_api_key or settings.openai_api_key == "sk-proj-your_openai_api_key_here":
        print("\n⚠️  경고: OpenAI API 키가 설정되지 않았습니다!")
        print("📝 .env 파일에 OPENAI_API_KEY를 설정해주세요.\n")
        sys.exit(1)
    
    # 이벤트 루프 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run()