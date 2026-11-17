"""聊天与会话管理路由。"""

import logging

from fastapi import APIRouter, Depends

from backend.deps import get_agent_service
from backend.errors import NotFoundError
from backend.schemas import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    SessionDeletedResponse,
)
from backend.services.agent_service import AgentService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    service: AgentService = Depends(get_agent_service),
) -> ChatResponse:
    """向 Agent 提问。

    - 不传 session_id（或传 null）：新建会话，响应中返回新 session_id；
    - 传已有 session_id：连续对话（上下文经 MemorySaver 保持）；
    - trace 结构与 agent/graph.py 一致：{"node", "action", "detail"}，
      detail 为列表（工具名）或字符串，个别条目可能缺省。

    说明：本端点为同步 def，FastAPI 自动放入线程池执行，
    长耗时 Agent 运行不会阻塞事件循环。
    """
    result = service.ask(payload.question, payload.session_id)
    return ChatResponse(**result)


@router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
def session_history(
    session_id: str,
    service: AgentService = Depends(get_agent_service),
) -> HistoryResponse:
    """获取指定会话的消息历史（服务侧记录，含每轮执行轨迹）。"""
    return HistoryResponse(**service.get_history(session_id))


@router.delete("/sessions/{session_id}", response_model=SessionDeletedResponse)
def delete_session(
    session_id: str,
    service: AgentService = Depends(get_agent_service),
) -> SessionDeletedResponse:
    """删除指定会话的服务侧记录。"""
    if not service.delete_session(session_id):
        raise NotFoundError(
            code="SESSION_NOT_FOUND", message=f"会话不存在：{session_id}"
        )
    return SessionDeletedResponse(success=True, session_id=session_id)
