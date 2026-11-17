from pathlib import Path

from agent.graph import EnterpriseAgent
from core.config import MAX_REFLECTIONS
from rag.vector_store import KnowledgeBase
from tools.calculator import calculator
from tools.knowledge import KnowledgeToolFactory
from tools.web_search import web_search
from core.tool_registry import ToolRegistry


def build_app():
    kb = KnowledgeBase()
    chunk_count = kb.build()
    print(f"知识库初始化完成：{chunk_count} 个文本块")

    knowledge_tool = KnowledgeToolFactory(kb).create()
    registry = ToolRegistry()
    for tool in (knowledge_tool, web_search, calculator):
        registry.register(tool)
    agent = EnterpriseAgent(
        registry.tools,
        max_reflections=MAX_REFLECTIONS,
    )
    return agent


def main():
    Path("data/documents").mkdir(parents=True, exist_ok=True)
    agent = build_app()
    print("\nEnterprise Agent 已启动，输入 exit 退出。")
    while True:
        question = input("\n你：").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        try:
            answer, trace = agent.ask(question)
            print("\n--- Agent 执行轨迹 ---")
            for item in trace:
                print(item)
            print("\nAgent：", answer)
        except Exception as exc:
            print("运行失败：", exc)


if __name__ == "__main__":
    main()
