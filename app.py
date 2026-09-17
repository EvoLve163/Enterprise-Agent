import os
from pathlib import Path

import streamlit as st

from agent.graph import EnterpriseAgent
from core.config import MAX_REFLECTIONS
from rag.vector_store import KnowledgeBase
from tools.calculator import calculator
from tools.knowledge import KnowledgeToolFactory
from tools.web_search import web_search
from core.tool_registry import ToolRegistry
from rag.document_manager import DocumentManager


st.set_page_config(page_title="Enterprise Agent", page_icon="🤖", layout="wide")
st.title("🤖 Enterprise Agent")
st.caption("LangGraph + RAG + Tool Calling + Reflection")

Path("data/documents").mkdir(parents=True, exist_ok=True)

document_manager = DocumentManager()
@st.cache_resource(show_spinner=False)
def build_agent():
    kb = KnowledgeBase()
    if not kb.load():
        chunk_count = kb.build()
    else:
        chunk_count = -1
    knowledge_tool = KnowledgeToolFactory(kb).create()
    registry = ToolRegistry()
    for tool in (knowledge_tool, web_search, calculator):
        registry.register(tool)
    agent = EnterpriseAgent(
        registry.tools,
        max_reflections=MAX_REFLECTIONS,
    )
    return agent, chunk_count

with st.sidebar:
    st.header("知识库")
    uploaded = st.file_uploader("上传 PDF", type=["pdf"])
    if uploaded:
        target = Path("data/documents") / uploaded.name
        target.write_bytes(uploaded.getbuffer())
        st.success(f"已保存：{uploaded.name}")
        st.cache_resource.clear()
        st.rerun()

    docs = list(Path("data/documents").glob("*.pdf"))
    st.write(f"当前 PDF：{len(docs)} 个")
    if Path("data/vector_store").exists():
        st.success("🟢 向量知识库已加载")
    else:
        st.warning("🟡 未检测到向量知识库")
    if st.button("重新构建知识库"):
        st.cache_resource.clear()
        st.rerun()

agent, chunk_count = build_agent()
st.sidebar.write(f"当前文本块：{chunk_count}")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit-user"

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("trace"):
            with st.expander("查看 Agent 执行轨迹"):
                for item in msg["trace"]:
                    st.write(item)

question = st.chat_input("例如：根据知识库说明公司的报销流程")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Agent 正在思考并调用工具..."):
            try:
                answer, trace = agent.ask(question, thread_id=st.session_state.thread_id)
                st.markdown(answer)
                if trace:
                    st.caption("本次回答由 Agent 自动检索并生成")
                with st.expander("查看 Agent 执行轨迹"):

                    for item in trace:

                        if isinstance(item, dict):

                            node = item.get("node","")

                            action = item.get("action","")

                            detail = item.get("detail","")

                            st.markdown(f"""
                                **节点：** {node}

                                **动作：** {action}

                                **详情：** {detail}

                                ---
                """
                            )

                        else:
                            st.write(item)
                st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace})
            except Exception as exc:
                st.error(f"运行失败：{exc}")
