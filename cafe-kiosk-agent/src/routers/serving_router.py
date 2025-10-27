"""
서빙 라우터 모듈
클라우드 모델과 로컬 모델 간의 라우팅을 관리합니다.
"""

import asyncio
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from src.services.llm_service import get_llm_service, ModelType
from config.settings import settings
from src.utils.logger import get_logger, LogContext


logger = get_logger(__name__)


class SensitivityLevel(str, Enum):
    """민감도 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ServingDecision:
    """서빙 결정 결과"""
    target: ModelType
    model_name: str
    sensitivity: SensitivityLevel
    reason: str
    fallback_available: bool = False
    
    def __repr__(self) -> str:
        return (
            f"ServingDecision(target={self.target.value}, "
            f"sensitivity={self.sensitivity.value})"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "target": self.target.value,
            "model_name": self.model_name,
            "sensitivity": self.sensitivity.value,
            "reason": self.reason,
            "fallback_available": self.fallback_available
        }


class ServingRouter:
    """서빙 전략 라우터"""
    
    # 민감한 키워드 (개인정보 관련)
    SENSITIVE_KEYWORDS = [
        "전화번호", "주소", "이메일", "카드", "계좌",
        "주민등록", "비밀번호", "개인정보",
        "phone", "address", "email", "card", "password",
        "personal", "private", "confidential"
    ]
    
    def __init__(self):
        """초기화"""
        self.llm_service = None
        self.local_model_status = {
            "available": False,
            "last_checked": None,
            "check_interval": timedelta(minutes=5)
        }
        self.serving_history: List[ServingDecision] = []
        logger.info("Serving Router initialized")
    
    async def _ensure_llm_service(self):
        """LLM 서비스 초기화 확인"""
        if self.llm_service is None:
            self.llm_service = await get_llm_service()
    
    async def route(
        self,
        query: str,
        force_local: bool = False,
        force_cloud: bool = False
    ) -> ServingDecision:
        """
        쿼리를 적절한 서빙 대상으로 라우팅
        
        Args:
            query: 질문 텍스트
            force_local: 로컬 모델 강제 사용
            force_cloud: 클라우드 모델 강제 사용
            
        Returns:
            ServingDecision: 서빙 결정
        """
        async with LogContext(logger, "serving_routing", query=query[:50]):
            await self._ensure_llm_service()
            
            # 강제 옵션 처리
            if force_cloud:
                return self._create_cloud_decision(
                    SensitivityLevel.LOW,
                    "Forced cloud serving"
                )
            
            if force_local:
                return await self._create_local_decision(
                    SensitivityLevel.HIGH,
                    "Forced local serving"
                )
            
            # 전략에 따른 라우팅
            if settings.model_strategy == "cloud_only":
                return self._create_cloud_decision(
                    SensitivityLevel.LOW,
                    "Cloud-only strategy"
                )
            
            if settings.model_strategy == "local_only":
                return await self._create_local_decision(
                    SensitivityLevel.MEDIUM,
                    "Local-only strategy"
                )
            
            # Auto 전략: 민감도와 가용성 기반
            return await self._auto_route(query)
    
    async def _auto_route(self, query: str) -> ServingDecision:
        """
        자동 라우팅 로직
        
        Args:
            query: 질문 텍스트
            
        Returns:
            ServingDecision: 서빙 결정
        """
        # 민감도 분석
        sensitivity = self._analyze_sensitivity_fast(query)
        
        # 로컬 모델 가용성 확인
        local_available = await self._check_local_availability()
        
        # 라우팅 로직
        if sensitivity == SensitivityLevel.HIGH:
            if local_available:
                # 고민감도 + 로컬 가능 -> 로컬
                decision = await self._create_local_decision(
                    sensitivity,
                    "High sensitivity, using local model for privacy"
                )
            else:
                # 고민감도 + 로컬 불가 -> 클라우드 (경고)
                logger.warning(
                    "High sensitivity query but local model unavailable"
                )
                decision = self._create_cloud_decision(
                    sensitivity,
                    "High sensitivity but local unavailable, using cloud with caution"
                )
        
        elif sensitivity == SensitivityLevel.LOW:
            # 저민감도 -> 클라우드 (더 나은 성능)
            decision = self._create_cloud_decision(
                sensitivity,
                "Low sensitivity, using cloud for better performance",
                fallback_available=local_available
            )
        
        else:
            # 중간 민감도 -> 로컬 우선, 없으면 클라우드
            if local_available:
                decision = await self._create_local_decision(
                    sensitivity,
                    "Medium sensitivity, local model available"
                )
            else:
                decision = self._create_cloud_decision(
                    sensitivity,
                    "Medium sensitivity, local unavailable, using cloud"
                )
        
        # 히스토리 저장
        self.serving_history.append(decision)
        
        logger.info(
            "Serving decision made",
            target=decision.target.value,
            sensitivity=decision.sensitivity.value,
            reason=decision.reason
        )
        
        return decision
    
    def _analyze_sensitivity_fast(self, query: str) -> SensitivityLevel:
        """
        빠른 민감도 분석 (키워드 기반)
        
        Args:
            query: 질문 텍스트
            
        Returns:
            SensitivityLevel: 민감도 수준
        """
        query_lower = query.lower()
        
        # 민감한 키워드 확인
        sensitive_count = sum(
            1 for keyword in self.SENSITIVE_KEYWORDS
            if keyword in query_lower
        )
        
        if sensitive_count >= 2:
            return SensitivityLevel.HIGH
        elif sensitive_count == 1:
            return SensitivityLevel.MEDIUM
        else:
            return SensitivityLevel.LOW
    
    async def analyze_sensitivity_with_llm(
        self,
        query: str
    ) -> SensitivityLevel:
        """
        LLM을 사용한 정밀 민감도 분석
        
        Args:
            query: 질문 텍스트
            
        Returns:
            SensitivityLevel: 민감도 수준
        """
        prompt = f"""
다음 질문의 민감도를 분석하라.

질문: {query}

민감도 기준:
- low: 일반적인 정보, 공개된 지식, 간단한 주문
- medium: 개인적인 의견, 약간 민감한 주제
- high: 개인정보, 기밀 정보, 매우 민감한 주제

민감도만 답변하라 (low, medium, high 중 하나).
        """
        
        try:
            response = await self.llm_service._call_openai(
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=10
            )
            
            sensitivity = response.strip().lower()
            
            if sensitivity not in ["low", "medium", "high"]:
                sensitivity = "medium"
            
            return SensitivityLevel(sensitivity)
        
        except Exception as e:
            logger.error(f"Failed to analyze sensitivity with LLM", error=str(e))
            return SensitivityLevel.MEDIUM
    
    async def _check_local_availability(self) -> bool:
        """
        로컬 모델 가용성 확인 (캐싱 포함)
        
        Returns:
            bool: 사용 가능 여부
        """
        now = datetime.now()
        
        # 최근에 확인했으면 캐시된 결과 사용
        if (self.local_model_status["last_checked"] and
            now - self.local_model_status["last_checked"] < 
            self.local_model_status["check_interval"]):
            return self.local_model_status["available"]
        
        # 새로 확인
        available = await self.llm_service.check_local_model_availability()
        
        self.local_model_status["available"] = available
        self.local_model_status["last_checked"] = now
        
        return available
    
    def _create_cloud_decision(
        self,
        sensitivity: SensitivityLevel,
        reason: str,
        fallback_available: bool = False
    ) -> ServingDecision:
        """
        클라우드 서빙 결정 생성
        
        Args:
            sensitivity: 민감도
            reason: 선택 이유
            fallback_available: 폴백 가능 여부
            
        Returns:
            ServingDecision: 서빙 결정
        """
        return ServingDecision(
            target=ModelType.CLOUD,
            model_name=settings.gpt_standard_model,
            sensitivity=sensitivity,
            reason=reason,
            fallback_available=fallback_available
        )
    
    async def _create_local_decision(
        self,
        sensitivity: SensitivityLevel,
        reason: str
    ) -> ServingDecision:
        """
        로컬 서빙 결정 생성
        
        Args:
            sensitivity: 민감도
            reason: 선택 이유
            
        Returns:
            ServingDecision: 서빙 결정
        """
        # 로컬 모델 가용성 최종 확인
        available = await self._check_local_availability()
        
        if not available:
            logger.warning("Local model not available, falling back to cloud")
            return self._create_cloud_decision(
                sensitivity,
                f"{reason} (fallback to cloud: local unavailable)"
            )
        
        return ServingDecision(
            target=ModelType.LOCAL,
            model_name=self.llm_service.ollama_model,
            sensitivity=sensitivity,
            reason=reason,
            fallback_available=True
        )
    
    async def route_batch(
        self,
        queries: List[str]
    ) -> List[ServingDecision]:
        """
        여러 쿼리를 배치로 라우팅
        
        Args:
            queries: 쿼리 리스트
            
        Returns:
            List[ServingDecision]: 서빙 결정 리스트
        """
        async with LogContext(logger, "batch_serving_routing", count=len(queries)):
            tasks = [self.route(query) for query in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            decisions = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to route query {i}", error=str(result))
                    # 기본 결정
                    decisions.append(self._create_cloud_decision(
                        SensitivityLevel.MEDIUM,
                        "Error fallback"
                    ))
                else:
                    decisions.append(result)
            
            return decisions
    
    def get_serving_stats(self) -> Dict[str, Any]:
        """
        서빙 통계
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        if not self.serving_history:
            return {
                "total_servings": 0,
                "target_distribution": {},
                "sensitivity_distribution": {},
                "local_availability_rate": 0.0
            }
        
        # 대상 분포
        target_dist = {}
        for decision in self.serving_history:
            target = decision.target.value
            target_dist[target] = target_dist.get(target, 0) + 1
        
        # 민감도 분포
        sensitivity_dist = {}
        for decision in self.serving_history:
            sens = decision.sensitivity.value
            sensitivity_dist[sens] = sensitivity_dist.get(sens, 0) + 1
        
        # 로컬 가용성 비율
        local_count = sum(
            1 for d in self.serving_history
            if d.target == ModelType.LOCAL or d.fallback_available
        )
        availability_rate = local_count / len(self.serving_history) * 100
        
        return {
            "total_servings": len(self.serving_history),
            "target_distribution": target_dist,
            "sensitivity_distribution": sensitivity_dist,
            "local_availability_rate": round(availability_rate, 2)
        }
    
    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        최근 결정 이력
        
        Args:
            limit: 조회 개수
            
        Returns:
            List[Dict[str, Any]]: 결정 이력
        """
        recent = self.serving_history[-limit:]
        return [d.to_dict() for d in recent]
    
    def clear_history(self):
        """결정 이력 초기화"""
        count = len(self.serving_history)
        self.serving_history.clear()
        logger.info(f"Serving decision history cleared", count=count)
    
    async def test_local_connection(self) -> Dict[str, Any]:
        """
        로컬 모델 연결 테스트
        
        Returns:
            Dict[str, Any]: 테스트 결과
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            available = await self.llm_service.check_local_model_availability()
            duration = asyncio.get_event_loop().time() - start_time
            
            return {
                "available": available,
                "response_time": round(duration, 3),
                "model_name": self.llm_service.ollama_model if available else None,
                "status": "success" if available else "unavailable"
            }
        
        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time
            
            return {
                "available": False,
                "response_time": round(duration, 3),
                "model_name": None,
                "status": "error",
                "error": str(e)
            }


# 싱글톤 인스턴스
_serving_router: Optional[ServingRouter] = None


def get_serving_router() -> ServingRouter:
    """
    서빙 라우터 인스턴스 반환
    
    Returns:
        ServingRouter: 서빙 라우터 인스턴스
    """
    global _serving_router
    if _serving_router is None:
        _serving_router = ServingRouter()
    return _serving_router
