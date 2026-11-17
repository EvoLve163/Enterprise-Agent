"""Pydantic 请求/响应模型（与前端 API 类型一一对应）。"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# 会话标识：字母/数字/下划线/连字符，1~64 位。
# session_id 同时作为 LangGraph thread_id 使用，禁止特殊字符。
SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


# ---------------- 聊天 ----------------


class TraceItem(BaseModel):
    """单条执行轨迹。结构与 agent/graph.py 中 trace.append 的字典一致：
    {"node": ..., "action": ..., "detail": ...}。
    注意：graph.py:77-83 的 blocked_duplicate_tool 条目没有 detail 键，
    因此 detail 为可选字段。
    """

    node: str = ""
    action: str = ""
    detail: Any = None


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户问题",
        examples=["根据知识库说明公司的报销流程"],
    )
    session_id: Optional[str] = Field(
        None,
        pattern=SESSION_ID_PATTERN,
        description="会话标识；为空则新建会话并在响应中返回新 session_id",
        examples=["a3f9c2e8d1b74f0e9c6d5a7b8e2f1c04"],
    )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    trace: Optional[list[TraceItem]] = None
    created_at: datetime


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    trace: list[TraceItem]
    elapsed_ms: int


class HistoryResponse(BaseModel):
    session_id: str
    count: int
    messages: list[ChatMessage]


class SessionDeletedResponse(BaseModel):
    success: bool
    session_id: str


# ---------------- 文档管理 ----------------


class DocumentInfo(BaseModel):
    filename: str
    size_bytes: int
    modified_at: datetime


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentInfo]


class UploadResponse(BaseModel):
    filename: str
    chunks: int = Field(..., description="本次新增的向量块数")
    warning: Optional[str] = None


class DocumentDeletedResponse(BaseModel):
    success: bool
    file: str
    remaining_chunks: int = Field(..., description="删除并重建后知识库剩余向量块数")


class RebuildResponse(BaseModel):
    chunks: int = Field(..., description="全量重建后的向量块总数")


# ---------------- 评测 ----------------


class EvaluationRunResponse(BaseModel):
    status: str = Field(..., description="启动后恒为 running")
    total_cases: int = Field(..., description="本次评测用例总数")


class EvaluationCaseResult(BaseModel):
    index: int
    question: str
    type: str = ""
    answer: str = ""
    expected_keywords: list[str] = []
    matched_keywords: list[str] = []
    missed_keywords: list[str] = []
    score: float = Field(..., ge=0.0, le=1.0, description="关键词命中率 0~1")
    elapsed_ms: int = 0
    error: Optional[str] = None


class EvaluationSummary(BaseModel):
    total: int
    executed: Optional[int] = None
    average_score: Optional[float] = None
    full_score_count: Optional[int] = None
    case_failed_count: Optional[int] = None


class EvaluationResultsResponse(BaseModel):
    status: str = Field(
        ...,
        description="idle（尚未执行过）| running | completed | failed",
    )
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    summary: Optional[EvaluationSummary] = None
    cases: Optional[list[EvaluationCaseResult]] = None


# ---------------- 健康检查 ----------------


class HealthResponse(BaseModel):
    status: str
    version: str
    agent_ready: bool
    document_count: int
    vector_store_loaded: bool
    llm_configured: bool
    web_search_configured: bool
