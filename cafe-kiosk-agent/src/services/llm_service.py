"""
LLM 통합 서비스 모듈
OpenAI 및 로컬 모델과의 통신을 관리합니다.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import json

from openai import AsyncOpenAI
import aiohttp

from config.settings import settings
from src.utils.logger import get_logger, log_execution_time


logger = get_logger(__name__)


class ModelType(str, Enum):
    """모델 타입"""
    CLOUD = "cloud"
    LOCAL = "local"


class ComplexityLevel(str, Enum):
    """복잡도 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LLMService:
    """LLM 통합 서비스"""
    
    def __init__(self):
        """초기화"""
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.ollama_url = settings.ollama_base_url
        self.ollama_model = settings.ollama_model
        self.local_available = False
        
        logger.info("LLM Service initialized", 
                   model_strategy=settings.model_strategy)
    
    async def check_local_model_availability(self) -> bool:
        """
        로컬 모델 사용 가능 여부 확인
        
        Returns:
            bool: 사용 가능 여부
        """
        if not settings.enable_local_model:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    self.local_available = response.status == 200
                    logger.debug(f"Local model availability: {self.local_available}")
                    return self.local_available
        except Exception as e:
            logger.warning(f"Failed to check local model: {str(e)}")
            self.local_available = False
            return False
    
    @log_execution_time(logger)
    async def classify_category(self, order_text: str) -> str:
        """
        주문 텍스트의 카테고리 분류
        
        Args:
            order_text: 주문 텍스트
            
        Returns:
            str: 카테고리 (음료, 디저트, 식사)
        """
        prompt = f"""
다음 주문 내용을 분석하여 가장 적절한 메뉴 카테고리를 선택하라.

주문 내용: {order_text}

카테고리: 음료, 디저트, 식사

카테고리 하나만 답변하라. 다른 설명은 포함하지 마라.
        """
        
        response = await self._call_openai(
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=10
        )
        
        category = response.strip()
        logger.info(f"Category classified", order_text=order_text, category=category)
        
        return category
    
    @log_execution_time(logger)
    async def extract_order_items(
        self, 
        order_text: str, 
        category: str,
        available_menus: List[str]
    ) -> List[Dict[str, Any]]:
        """
        주문 텍스트에서 메뉴 항목 추출
        
        Args:
            order_text: 주문 텍스트
            category: 카테고리
            available_menus: 사용 가능한 메뉴 리스트
            
        Returns:
            List[Dict[str, Any]]: 추출된 주문 항목 리스트
        """
        menu_list = ", ".join(available_menus)
        
        prompt = f"""다음 주문에서 메뉴와 수량을 추출하세요.

주문 내용: {order_text}
카테고리: {category}
사용 가능한 메뉴: {menu_list}

규칙:
1. menu는 반드시 사용 가능한 메뉴 중에서 선택
2. 수량이 명시되지 않으면 1로 설정
3. 사이즈는 Tall, Grande, Venti 중 하나 (없으면 null)
4. 온도는 Hot, Ice 중 하나 (없으면 null)
5. 유사한 메뉴 이름 매칭 (예: "아이스 아메리카노" → "아메리카노")

JSON만 출력하세요:
{{
    "items": [
        {{
            "menu": "메뉴명",
            "quantity": 1,
            "size": "Tall",
            "temperature": "Ice",
            "options": []
        }}
    ]
}}"""
        
        try:
            response = await self._call_openai(
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=500
            )
            
            # 빈 응답 체크
            if not response or response.strip() == "":
                logger.error("Empty response from LLM")
                return self._fallback_extraction(order_text, available_menus)
            
            # JSON 파싱
            try:
                # 마크다운 코드 블록 제거
                cleaned_response = response.replace('```json', '').replace('```', '').strip()
                
                # 빈 응답 재확인
                if not cleaned_response:
                    logger.error("Empty response after cleaning")
                    return self._fallback_extraction(order_text, available_menus)
                
                result = json.loads(cleaned_response)
                items = result.get("items", [])
                
                logger.info(
                    "Order items extracted",
                    order_text=order_text,
                    items_count=len(items)
                )
                
                return items
            except json.JSONDecodeError as e:
                logger.error(
                    "Failed to parse JSON response",
                    response=response[:200],  # 첫 200자만 로깅
                    error=str(e)
                )
                return self._fallback_extraction(order_text, available_menus)
        
        except Exception as e:
            logger.error(f"Failed to extract order items", error=str(e))
            return self._fallback_extraction(order_text, available_menus)
    
    def _fallback_extraction(
        self,
        order_text: str,
        available_menus: List[str]
    ) -> List[Dict[str, Any]]:
        """
        폴백 추출 로직 (간단한 키워드 매칭)
        
        Args:
            order_text: 주문 텍스트
            available_menus: 사용 가능한 메뉴 리스트
            
        Returns:
            List[Dict[str, Any]]: 추출된 항목
        """
        logger.info("Using fallback extraction")
        
        items = []
        order_lower = order_text.lower()
        
        # 메뉴 매칭
        for menu in available_menus:
            menu_lower = menu.lower()
            
            # 정확한 매칭 또는 부분 매칭
            if menu_lower in order_lower or any(
                part in order_lower 
                for part in menu_lower.split() 
                if len(part) > 2
            ):
                # 수량 추출
                quantity = 1
                for i in range(1, 10):
                    if str(i) in order_text:
                        quantity = i
                        break
                
                # 사이즈 추출
                size = None
                if "톨" in order_lower or "tall" in order_lower:
                    size = "Tall"
                elif "그란데" in order_lower or "grande" in order_lower:
                    size = "Grande"
                elif "벤티" in order_lower or "venti" in order_lower:
                    size = "Venti"
                
                # 온도 추출
                temperature = None
                if "아이스" in order_lower or "ice" in order_lower or "차가" in order_lower:
                    temperature = "Ice"
                elif "핫" in order_lower or "hot" in order_lower or "뜨거" in order_lower:
                    temperature = "Hot"
                
                items.append({
                    "menu": menu,
                    "quantity": quantity,
                    "size": size,
                    "temperature": temperature,
                    "options": []
                })
                
                break  # 첫 번째 매칭만 사용
        
        logger.info(f"Fallback extraction found {len(items)} items")
        return items
    
    @log_execution_time(logger)
    async def analyze_complexity(self, query: str) -> ComplexityLevel:
        """
        질문의 복잡도 분석
        
        Args:
            query: 질문 텍스트
            
        Returns:
            ComplexityLevel: 복잡도 수준
        """
        prompt = f"""
다음 질문의 복잡도를 분석하라.

질문: {query}

복잡도 기준:
- low: 단순 사실 확인, 간단한 계산, 일반 상식, 간단한 주문
- medium: 설명이 필요한 개념, 비교 분석, 중간 수준의 추론, 옵션이 있는 주문
- high: 복잡한 추론, 창의적 작성, 다단계 분석, 복잡한 커스터마이징

복잡도만 답변하라 (low, medium, high 중 하나).
        """
        
        response = await self._call_openai(
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=10
        )
        
        complexity = response.strip().lower()
        
        # 유효성 검증
        if complexity not in ["low", "medium", "high"]:
            complexity = "medium"
        
        logger.info(f"Complexity analyzed", query=query[:50], complexity=complexity)
        
        return ComplexityLevel(complexity)
    
    @log_execution_time(logger)
    async def generate_recommendation(
        self,
        order_items: List[Dict[str, Any]],
        available_menus: Dict[str, Any]
    ) -> str:
        """
        주문에 대한 추천 생성
        
        Args:
            order_items: 현재 주문 항목
            available_menus: 사용 가능한 메뉴 정보
            
        Returns:
            str: 추천 메시지
        """
        items_str = ", ".join([f"{item['menu']} {item['quantity']}개" for item in order_items])
        
        prompt = f"""
고객이 다음 항목을 주문했습니다:
{items_str}

이 주문에 어울리는 추가 메뉴를 1-2개 추천해주세요.
추천 이유와 함께 간단하고 친절하게 설명하세요.
한국어로 답변하세요.
        """
        
        response = await self._call_openai(
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=200
        )
        
        logger.info("Recommendation generated", items_count=len(order_items))
        
        return response
    
    async def select_model_by_complexity(
        self, 
        complexity: ComplexityLevel
    ) -> tuple[ModelType, str]:
        """
        복잡도에 따른 모델 선택
        
        Args:
            complexity: 복잡도 수준
            
        Returns:
            tuple[ModelType, str]: (모델 타입, 모델 이름)
        """
        # 전략에 따른 강제 선택
        if settings.model_strategy == "cloud_only":
            return ModelType.CLOUD, settings.gpt_standard_model
        
        if settings.model_strategy == "local_only":
            if await self.check_local_model_availability():
                return ModelType.LOCAL, self.ollama_model
            else:
                logger.warning("Local model not available, falling back to cloud")
                return ModelType.CLOUD, settings.gpt_nano_model
        
        # Auto 전략
        if complexity == ComplexityLevel.LOW:
            model = settings.gpt_nano_model
        elif complexity == ComplexityLevel.MEDIUM:
            model = settings.gpt_mini_model
        else:
            model = settings.gpt_standard_model
        
        return ModelType.CLOUD, model
    
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_completion_tokens: int = 1000,
        model: Optional[str] = None
    ) -> str:
        """
        OpenAI API 호출
        
        Args:
            messages: 메시지 리스트
            max_completion_tokens: 최대 토큰 수
            model: 모델 이름
            
        Returns:
            str: 응답 텍스트
        """
        if model is None:
            model = settings.gpt_standard_model
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                timeout=settings.request_timeout
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"OpenAI API call failed", error=str(e))
            raise
    
    async def _call_ollama(
        self,
        prompt: str,
    ) -> str:
        """
        Ollama 로컬 모델 호출
        
        Args:
            prompt: 프롬프트
            
        Returns:
            str: 응답 텍스트
        """
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,

        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=settings.request_timeout)
                ) as response:
                    result = await response.json()
                    return result.get("response", "")
        
        except Exception as e:
            logger.error(f"Ollama API call failed", error=str(e))
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_type: Optional[ModelType] = None,
        model_name: Optional[str] = None,
        max_completion_tokens: int = 1000
    ) -> str:
        """
        통합 채팅 완성 API
        
        Args:
            messages: 메시지 리스트
            model_type: 모델 타입
            model_name: 모델 이름
            max_completion_tokens: 최대 토큰 수
            
        Returns:
            str: 응답 텍스트
        """
        if model_type == ModelType.LOCAL:
            # 로컬 모델은 단일 프롬프트로 변환
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            return await self._call_ollama(prompt)
        else:
            # 클라우드 모델
            return await self._call_openai(
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                model=model_name
            )
    
    async def batch_classify_categories(
        self, 
        order_texts: List[str]
    ) -> List[str]:
        """
        여러 주문의 카테고리를 배치로 분류
        
        Args:
            order_texts: 주문 텍스트 리스트
            
        Returns:
            List[str]: 카테고리 리스트
        """
        tasks = [self.classify_category(text) for text in order_texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        categories = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to classify order {i}",
                    error=str(result)
                )
                categories.append("음료")  # 기본값
            else:
                categories.append(result)
        
        return categories
    
    async def close(self):
        """리소스 정리"""
        await self.openai_client.close()
        logger.info("LLM Service closed")


# 싱글톤 인스턴스
_llm_service: Optional[LLMService] = None


async def get_llm_service() -> LLMService:
    """
    LLM 서비스 인스턴스 반환
    
    Returns:
        LLMService: LLM 서비스 인스턴스
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
        await _llm_service.check_local_model_availability()
    return _llm_service