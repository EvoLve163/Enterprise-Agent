"""Agent 服务：会话管理 + 现有 EnterpriseAgent 的调用封装。

设计要点：
- 直接复用 EnterpriseAgent（agent/graph.py），不重新实现 Agent；
- 由 backend/bootstrap.py 在进程启动时构建一次，Embedding 模型与 FAISS
  只加载一次，聊天请求零重复加载；
- session_id 同时作为前端会话标识与 LangGraph thread_id：连续对话由
  MemorySaver 检查点保持；不同 session_id 即不同 thread，互不串味；
- 每个会话独立 threading.Lock：同一会话的并发请求串行执行，避免同一
  thread 的消息交叉写入；不同会话可并行；
- 会话记录带 LRU 上限（默认 200 条），防止内存无限增长。被淘汰的只是
  服务侧历史记录，LangGraph 检查点仍在，旧 session_id 再次使用时仍能
  接续上下文（会重新建立服务侧记录）。
"""

import logging
import re
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.agent.graph import EnterpriseAgent

from backend.errors import BadRequestError, NotFoundError, UpstreamError
from backend.schemas import SESSION_ID_PATTERN

logger = logging.getLogger(__name__)

_SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)


@dataclass
class _Turn:
    role: str
    content: str
    trace: Optional[list]
    created_at: datetime


@dataclass
class _Session:
    session_id: str
    created_at: datetime
    lock: threading.Lock = field(default_factory=threading.Lock)
    turns: list = field(default_factory=list)


class AgentService:
    def __init__(self, agent: EnterpriseAgent, max_sessions: int = 200) -> None:
        self._agent = agent
        self._max_sessions = max_sessions
        self._sessions: "OrderedDict[str, _Session]" = OrderedDict()
        self._registry_lock = threading.Lock()

    # ---------------- 内部 ----------------

    def _session(self, session_id: str, create: bool) -> Optional[_Session]:
        with self._registry_lock:
            session = self._sessions.get(session_id)
            if session is None and create:
                session = _Session(session_id=session_id, created_at=datetime.now())
                self._sessions[session_id] = session
            if session is not None:
                # LRU：最近访问的会话移到队尾，超限时淘汰队首最旧会话
                self._sessions.move_to_end(session_id)
                while len(self._sessions) > self._max_sessions:
                    evicted, _ = self._sessions.popitem(last=False)
                    logger.warning(
                        "会话数超过上限 %s，淘汰最旧会话记录：%s", self._max_sessions, evicted
                    )
            return session

    # ---------------- 对外 ----------------

    def ask(self, question: str, session_id: Optional[str] = None) -> dict:
        """调用 Agent 回答问题；返回 {session_id, answer, trace, elapsed_ms}。"""
        question = (question or "").strip()
        if not question:
            raise BadRequestError(code="EMPTY_QUESTION", message="问题不能为空")
        if session_id is not None and not _SESSION_ID_RE.fullmatch(session_id):
            raise BadRequestError(
                code="INVALID_SESSION_ID",
                message="session_id 只能包含字母、数字、下划线、连字符，最长 64 位",
            )

        if not session_id:
            session_id = uuid.uuid4().hex
        session = self._session(session_id, create=True)

        # 同一会话串行执行：防止同一 thread 的状态交叉写入
        with session.lock:
            started = time.perf_counter()
            try:
                answer, trace = self._agent.ask(question, thread_id=session_id)
            except Exception as exc:
                logger.exception("Agent 执行失败（session=%s）", session_id)
                raise UpstreamError(
                    code="AGENT_RUN_FAILED", message=f"Agent 执行失败：{exc}"
                ) from exc
            elapsed_ms = int((time.perf_counter() - started) * 1000)

            now = datetime.now()
            session.turns.append(_Turn("user", question, None, now))
            session.turns.append(_Turn("assistant", str(answer), list(trace or []), now))

            return {
                "session_id": session_id,
                "answer": str(answer),
                "trace": list(trace or []),
                "elapsed_ms": elapsed_ms,
            }

    def get_history(self, session_id: str) -> dict:
        """返回服务侧维护的会话消息历史；未知会话抛 404。"""
        session = self._session(session_id, create=False)
        if session is None:
            raise NotFoundError(
                code="SESSION_NOT_FOUND", message=f"会话不存在：{session_id}"
            )
        return {
            "session_id": session_id,
            "count": len(session.turns),
            "messages": [
                {
                    "role": t.role,
                    "content": t.content,
                    "trace": t.trace,
                    "created_at": t.created_at,
                }
                for t in session.turns
            ],
        }

    def delete_session(self, session_id: str) -> bool:
        """删除会话记录；返回是否存在。"""
        with self._registry_lock:
            return self._sessions.pop(session_id, None) is not None
