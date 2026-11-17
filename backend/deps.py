"""FastAPI 依赖注入：从 app.state.runtime 获取进程级单例服务。

单例在 main.py 的 lifespan 中通过 bootstrap.build_runtime() 构建一次，
之后所有请求复用，Embedding 模型与 FAISS 不会重复加载。
"""

from fastapi import Request

from backend.bootstrap import Runtime
from backend.services.agent_service import AgentService
from backend.services.document_service import DocumentService
from backend.services.evaluation_service import EvaluationService


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


def get_agent_service(request: Request) -> AgentService:
    return get_runtime(request).agent_service


def get_document_service(request: Request) -> DocumentService:
    return get_runtime(request).document_service


def get_evaluation_service(request: Request) -> EvaluationService:
    return get_runtime(request).evaluation_service
