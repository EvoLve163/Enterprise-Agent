"""组合根：进程启动时构建一次单例对象图。

装配链（与 app.py / cli.py 的装配逻辑一致，但路径全部绝对化）：

    DocumentManager(绝对路径)
        └── knowledge_base: KnowledgeBase   ← 同一实例！
                └── KnowledgeToolFactory(kb).create()   ← 工具闭包捕获同一个 kb
                        └── ToolRegistry(knowledge_search / web_search / calculator)
                                └── EnterpriseAgent(tools, max_reflections)

关键不变量：knowledge_search 工具闭包里的 kb 与 DocumentManager.knowledge_base
是同一个对象，因此上传/删除文档对进行中的会话立即生效
（add_document / rebuild_without_file 直接替换该实例的 vector_store 属性）。

路径说明：现有 DocumentManager 默认用相对 CWD 的路径、KnowledgeBase 用项目根，
两者在 CWD != 项目根时会分裂；这里显式传项目根绝对路径规避该问题，
无需修改任何现有代码。
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from backend.agent.graph import EnterpriseAgent
from backend.core.config import MAX_REFLECTIONS
from backend.core.tool_registry import ToolRegistry
from backend.rag.document_manager import DocumentManager
from backend.rag.vector_store import KnowledgeBase
from backend.tools.calculator import calculator
from backend.tools.knowledge import KnowledgeToolFactory
from backend.tools.web_search import web_search

from backend.services.agent_service import AgentService
from backend.services.document_service import DocumentService
from backend.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)

# backend/bootstrap.py -> backend/ -> 项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"


@dataclass
class Runtime:
    agent_service: AgentService
    document_service: DocumentService
    evaluation_service: EvaluationService


def build_runtime() -> Runtime:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 文档管理器 + 知识库（共享同一 KnowledgeBase 实例）
    document_manager = DocumentManager(documents_dir=str(DOCUMENTS_DIR))
    kb = document_manager.knowledge_base
    # KnowledgeBase.load()（rag/vector_store.py:222-232）在 vector_store 目录
    # 存在但索引文件缺失/损坏时会【抛异常】而非返回 False（全新 clone 忽略
    # FAISS 二进制后即此状态），必须捕获后走全量重建，否则启动即崩溃。
    try:
        loaded = kb.load()
    except Exception:
        logger.warning("FAISS 索引加载失败（缺失或损坏），将全量重建", exc_info=True)
        loaded = False
    if not loaded:
        chunk_count = kb.build()
        if chunk_count == 0:
            logger.warning("知识库为空（data/documents 下没有 PDF），knowledge_search 将返回空结果")
        else:
            logger.info("未检测到 FAISS 索引，已全量构建：%s 个文本块", chunk_count)
    else:
        logger.info("FAISS 索引加载完成：%s", kb.vector_store_dir)

    # 2. 工具注册 + Agent
    knowledge_tool = KnowledgeToolFactory(kb).create()
    registry = ToolRegistry()
    for tool_obj in (knowledge_tool, web_search, calculator):
        registry.register(tool_obj)

    agent = EnterpriseAgent(registry.tools, max_reflections=MAX_REFLECTIONS)

    logger.info("Agent 组合根构建完成（工具：%s）", [t.name for t in registry.tools])

    return Runtime(
        agent_service=AgentService(agent),
        document_service=DocumentService(document_manager),
        evaluation_service=EvaluationService(agent),
    )
