"""Enterprise Agent 的 FastAPI 后端。

本包只做 HTTP 封装与会话/安全管理，业务实现全部复用现有
agent/ core/ rag/ tools/ 包，不重复实现 RAG 与 Agent。
"""

__version__ = "0.1.0"
