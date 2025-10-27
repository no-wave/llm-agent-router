"""
모델 라우터 모듈
질문의 복잡도에 따라 최적의 LLM 모델을 선택합니다.
"""

import asyncio
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from src.services.llm_service import (
    get_llm_service,
    ModelType,
    ComplexityLevel
)
from config.settings import settings
from src.utils.logger import get_logger, LogContext


logger = get_logger(__name__)


@dataclass
class ModelSelection:
    """모델 선택 결과"""
    model_type: ModelType
    model_name: str
    complexity: ComplexityLevel
    reason: str
    estimated_cost: float = 0.0
    
    def __repr__(self) -> str:
        return (
            f"ModelSelection(type={self.model_type.value}, "
            f"name={self.model_name}, complexity={self.complexity.value})"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "model_type": self.model_type.value,
            "model_name": self.model_name,
            "complexity": self.complexity.value,
            "reason": self.reason,
            "estimated_cost": self.estimated_cost
        }


class ModelRouter:
    """모델 선택 라우터"""
    
    # 모델별 상대적 비용 (임의 단위)
    MODEL_COSTS = {
        "gpt-5-nano": 1.0,
        "gpt-5-mini": 3.0,
        "gpt-5": 5.0,
    }
    
    def __init__(self):
        """초기화"""
        self.llm_service = None
        self.selection_history: List[ModelSelection] = []
        logger.info("Model Router initialized", strategy=settings.model_strategy)
    
    async def _ensure_llm_service(self):
        """LLM 서비스 초기화 확인"""
        if self.llm_service is None:
            self.llm_service = await get_llm_service()
    
    async def route(
        self,
        query: str,
        force_complexity: Optional[ComplexityLevel] = None
    ) -> ModelSelection:
        """
        쿼리 복잡도에 따라 모델 선택
        
        Args:
            query: 질문 텍스트
            force_complexity: 강제 복잡도 설정 (테스트용)
            
        Returns:
            ModelSelection: 모델 선택 결과
        """
        async with LogContext(logger, "model_routing", query=query[:50]):
            await self._ensure_llm_service()
            
            # 복잡도 분석
            if force_complexity:
                complexity = force_complexity
                reason = "Forced complexity level"
            else:
                try:
                    complexity = await self.llm_service.analyze_complexity(query)
                    reason = "LLM-analyzed complexity"
                except Exception as e:
                    logger.error(f"Failed to analyze complexity", error=str(e))
                    complexity = ComplexityLevel.MEDIUM
                    reason = "Fallback to medium complexity"
            
            # 모델 선택
            model_type, model_name = await self._select_model_by_strategy(complexity)
            
            # 비용 추정
            estimated_cost = self._estimate_cost(model_name, len(query))
            
            selection = ModelSelection(
                model_type=model_type,
                model_name=model_name,
                complexity=complexity,
                reason=reason,
                estimated_cost=estimated_cost
            )
            
            # 히스토리 저장
            self.selection_history.append(selection)
            
            logger.info(
                "Model selected",
                model_name=model_name,
                complexity=complexity.value,
                estimated_cost=estimated_cost
            )
            
            return selection
    
    async def _select_model_by_strategy(
        self,
        complexity: ComplexityLevel
    ) -> Tuple[ModelType, str]:
        """
        전략에 따른 모델 선택
        
        Args:
            complexity: 복잡도 수준
            
        Returns:
            Tuple[ModelType, str]: (모델 타입, 모델 이름)
        """
        # 강제 전략
        if settings.model_strategy == "cloud_only":
            return await self._select_cloud_model(complexity)
        
        if settings.model_strategy == "local_only":
            return await self._select_local_model(complexity)
        
        # Auto 전략: 복잡도와 가용성에 따라 선택
        return await self._select_auto_model(complexity)
    
    async def _select_cloud_model(
        self,
        complexity: ComplexityLevel
    ) -> Tuple[ModelType, str]:
        """
        클라우드 모델 선택
        
        Args:
            complexity: 복잡도 수준
            
        Returns:
            Tuple[ModelType, str]: (모델 타입, 모델 이름)
        """
        model_map = {
            ComplexityLevel.LOW: settings.gpt_nano_model,
            ComplexityLevel.MEDIUM: settings.gpt_mini_model,
            ComplexityLevel.HIGH: settings.gpt_standard_model
        }
        
        model_name = model_map.get(complexity, settings.gpt_mini_model)
        return ModelType.CLOUD, model_name
    
    async def _select_local_model(
        self,
        complexity: ComplexityLevel
    ) -> Tuple[ModelType, str]:
        """
        로컬 모델 선택
        
        Args:
            complexity: 복잡도 수준
            
        Returns:
            Tuple[ModelType, str]: (모델 타입, 모델 이름)
        """
        # 로컬 모델 가용성 확인
        available = await self.llm_service.check_local_model_availability()
        
        if available:
            return ModelType.LOCAL, self.llm_service.ollama_model
        else:
            logger.warning("Local model not available, falling back to cloud")
            return await self._select_cloud_model(ComplexityLevel.LOW)
    
    async def _select_auto_model(
        self,
        complexity: ComplexityLevel
    ) -> Tuple[ModelType, str]:
        """
        자동 모델 선택 (복잡도와 가용성 기반)
        
        Args:
            complexity: 복잡도 수준
            
        Returns:
            Tuple[ModelType, str]: (모델 타입, 모델 이름)
        """
        # 간단한 쿼리는 로컬 모델 시도
        if complexity == ComplexityLevel.LOW:
            available = await self.llm_service.check_local_model_availability()
            if available:
                return ModelType.LOCAL, self.llm_service.ollama_model
        
        # 복잡한 쿼리나 로컬 모델 없을 시 클라우드 사용
        return await self._select_cloud_model(complexity)
    
    def _estimate_cost(self, model_name: str, query_length: int) -> float:
        """
        비용 추정 (상대적)
        
        Args:
            model_name: 모델 이름
            query_length: 쿼리 길이
            
        Returns:
            float: 추정 비용
        """
        base_cost = self.MODEL_COSTS.get(model_name, 1.0)
        
        # 쿼리 길이에 따른 가중치 (대략적)
        length_factor = 1 + (query_length / 1000)
        
        return round(base_cost * length_factor, 2)
    
    async def route_batch(
        self,
        queries: List[str]
    ) -> List[ModelSelection]:
        """
        여러 쿼리를 배치로 라우팅
        
        Args:
            queries: 쿼리 리스트
            
        Returns:
            List[ModelSelection]: 모델 선택 결과 리스트
        """
        async with LogContext(logger, "batch_model_routing", count=len(queries)):
            tasks = [self.route(query) for query in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            selections = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to route query {i}", error=str(result))
                    # 기본 선택
                    selections.append(ModelSelection(
                        model_type=ModelType.CLOUD,
                        model_name=settings.gpt_nano_model,
                        complexity=ComplexityLevel.MEDIUM,
                        reason="Error fallback"
                    ))
                else:
                    selections.append(result)
            
            return selections
    
    def get_selection_stats(self) -> Dict[str, Any]:
        """
        모델 선택 통계
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        if not self.selection_history:
            return {
                "total_selections": 0,
                "model_usage": {},
                "complexity_distribution": {},
                "total_estimated_cost": 0.0
            }
        
        # 모델별 사용 횟수
        model_usage = {}
        for selection in self.selection_history:
            model = selection.model_name
            model_usage[model] = model_usage.get(model, 0) + 1
        
        # 복잡도 분포
        complexity_dist = {}
        for selection in self.selection_history:
            comp = selection.complexity.value
            complexity_dist[comp] = complexity_dist.get(comp, 0) + 1
        
        # 총 비용
        total_cost = sum(s.estimated_cost for s in self.selection_history)
        
        return {
            "total_selections": len(self.selection_history),
            "model_usage": model_usage,
            "complexity_distribution": complexity_dist,
            "total_estimated_cost": round(total_cost, 2),
            "average_cost": round(total_cost / len(self.selection_history), 2)
        }
    
    def get_recent_selections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        최근 선택 이력
        
        Args:
            limit: 조회 개수
            
        Returns:
            List[Dict[str, Any]]: 선택 이력
        """
        recent = self.selection_history[-limit:]
        return [s.to_dict() for s in recent]
    
    def clear_history(self):
        """선택 이력 초기화"""
        count = len(self.selection_history)
        self.selection_history.clear()
        logger.info(f"Model selection history cleared", count=count)
    
    async def recommend_model_for_task(
        self,
        task_description: str
    ) -> ModelSelection:
        """
        작업 설명에 따른 모델 추천
        
        Args:
            task_description: 작업 설명
            
        Returns:
            ModelSelection: 추천 모델
        """
        # 키워드 기반 빠른 판단
        task_lower = task_description.lower()
        
        # High complexity 키워드
        high_keywords = [
            "분석", "추론", "복잡", "상세", "전략", "계획",
            "analyze", "complex", "detailed", "strategy"
        ]
        
        # Low complexity 키워드
        low_keywords = [
            "간단", "단순", "확인", "yes/no", "simple", "check"
        ]
        
        if any(keyword in task_lower for keyword in high_keywords):
            complexity = ComplexityLevel.HIGH
        elif any(keyword in task_lower for keyword in low_keywords):
            complexity = ComplexityLevel.LOW
        else:
            complexity = ComplexityLevel.MEDIUM
        
        return await self.route(task_description, force_complexity=complexity)


# 싱글톤 인스턴스
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """
    모델 라우터 인스턴스 반환
    
    Returns:
        ModelRouter: 모델 라우터 인스턴스
    """
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router
