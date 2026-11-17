"""Enterprise Agent 后端服务入口。

启动（以项目根为工作目录）：
    .venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

接口文档：
    Swagger UI  http://127.0.0.1:8000/docs
    ReDoc       http://127.0.0.1:8000/redoc
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend import __version__
from backend.bootstrap import build_runtime
from backend.errors import AppError
from backend.routers import chat, documents, evaluation
from backend.schemas import HealthResponse
from core.config import LLM_API_KEY, SERPAPI_API_KEY

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("backend")

# 开发环境允许的本地前端源（Vite 默认 5173 / vue-cli 默认 8080）
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """进程启动时一次性构建单例对象图。

    Embedding 模型与 FAISS 索引在此加载一次，之后所有
    聊天 / 文档请求直接复用，不存在重复加载。
    """
    logger.info("后端运行时初始化中（加载 Embedding 模型与 FAISS 索引）……")
    app.state.runtime = build_runtime()
    logger.info("后端运行时就绪")
    yield
    app.state.runtime = None
    logger.info("后端运行时已释放")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise Agent API",
        description=(
            "现有 LangGraph + RAG + Tool Calling + Reflection Agent 的 FastAPI 封装层。\n\n"
            "业务实现全部复用现有 agent/ core/ rag/ tools/ 包，本层只负责：\n"
            "HTTP 契约、会话管理、安全校验与并发控制。"
        ),
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------- 异常处理 ----------------

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """业务异常：统一返回 {"detail": {"code", "message"}}。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """框架 HTTP 异常（如未路由 404、405）使用同一错误格式。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数校验失败",
                    "errors": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常：%s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "INTERNAL_ERROR", "message": "服务器内部错误，请查看后端日志"}},
        )

    # ---------------- 路由 ----------------

    app.include_router(chat.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(evaluation.router, prefix="/api")

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health(request: Request) -> HealthResponse:
        """健康检查。只返回状态与布尔标记，不暴露任何 Key/敏感配置。"""
        runtime = getattr(request.app.state, "runtime", None)
        docs = runtime.document_service.list_documents() if runtime else []
        return HealthResponse(
            status="ok",
            version=__version__,
            agent_ready=runtime is not None,
            document_count=len(docs),
            vector_store_loaded=bool(runtime and runtime.document_service.vector_store_loaded),
            llm_configured=bool(LLM_API_KEY),
            web_search_configured=bool(SERPAPI_API_KEY),
        )

    return app


app = create_app()
