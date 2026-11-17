"""评测管理路由。

- POST /api/evaluation/run     启动一次评测（后台执行，立即返回）
- GET  /api/evaluation/results 最近一次评测的状态与结果

前端不直接执行任何 Python；评测只在本服务内通过现有
evaluation/evaluator.py 的用例与评分函数 + 现有 Agent 单例执行。
"""

import logging

from fastapi import APIRouter, Depends, status

from backend.deps import get_evaluation_service
from backend.schemas import (
    EvaluationRunResponse,
    EvaluationResultsResponse,
)
from backend.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_evaluation(
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse:
    """启动评测任务。已有评测在执行中时返回 409 EVALUATION_ALREADY_RUNNING。"""
    result = service.start_run()
    return EvaluationRunResponse(**result)


@router.get("/results", response_model=EvaluationResultsResponse)
def evaluation_results(
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationResultsResponse:
    """获取最近一次评测的状态与结果（服务启动后未跑过时 status=idle）。"""
    return EvaluationResultsResponse(**service.get_results())
