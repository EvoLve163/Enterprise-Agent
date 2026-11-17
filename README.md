# Enterprise Agent

基于 LangGraph + LangChain + RAG + Tool Calling + Reflection 的企业智能知识与业务助手。

这个项目专门按“大模型应用开发 / Agent / RAG / LangChain / LangGraph / Prompt 工程”岗位方向设计，并把你已有的 PDF RAG 代码升级为 Agent 架构。

## 1. 项目能力

- 企业知识库 RAG：PDF -> 分块 -> 本地 Embedding -> FAISS
- Agent 自主工具选择：知识库检索 / Web Search / Calculator
- LangGraph 状态化工作流：Agent -> Tools -> Agent 循环
- Reflection：最终答案二次检查，不足时要求 Agent 修正
- 对话历史：支持多轮问答
- Streamlit UI：上传 PDF、聊天、查看 Agent 执行轨迹

## 2. 环境

Python 3.10+ 推荐。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 配置

复制：

```text
.env.example -> .env
```

填写你的 DeepSeek API Key。DeepSeek 当前提供 OpenAI 兼容接口，官方文档当前推荐 OpenAI base_url 使用 `https://api.deepseek.com`；当前 API 文档列出的模型包含 `deepseek-v4-flash`。如果你已有其它 OpenAI-compatible 服务，也可以替换三个 LLM 环境变量。

SERPAPI_API_KEY 可选；没有它时 Web Search 工具会返回“未配置”，不会阻塞本地 RAG。

## 4. 放入知识库

将企业资料 PDF 放到：

```text
data/documents/
```

运行 CLI：

```bash
python cli.py
```

启动 Web UI：

```bash
streamlit run app.py
```

## 5. 推荐测试问题

1. “根据企业知识库，公司的报销流程是什么？”
2. “知识库里没有的信息，帮我联网查一下。”
3. “根据知识库和公开资料，对比两个产品的特点。”
4. “计算今年和去年的销售额增长率：今年 1280 万，去年 1000 万。”
5. “请告诉我答案依据了哪些文档。”

## 6. 项目与 Hello Agents 前 7 章的对应关系

- 第1~3章：LLM、Prompt、Token、模型调用 -> `core/llm.py`、`agent/prompts.py`
- 第4章：ReAct / Planning / Reflection / Tool -> `agent/graph.py`、`tools/`
- 第5章：低代码 Workflow 思维 -> 项目先按工作流验证，再代码化
- 第6章：LangGraph / LangChain -> `StateGraph`、`ToolNode`
- 第7章：Agent 框架内部机制 -> `agent/graph.py`、`core/llm.py`、工具抽象

## 7. 简历定位

建议项目名：

**Enterprise Agent——基于 LangGraph 的企业智能知识与业务助手**

建议简历描述：

- 基于 LangChain + LangGraph 构建状态化企业智能 Agent，实现知识库检索、Web Search、Calculator 等多工具自主调用。
- 基于 PDF Loader、RecursiveCharacterTextSplitter、BGE Embedding 与 FAISS 构建企业知识库 RAG，实现文档分块、向量检索及来源溯源。
- 基于 ReAct 思路设计 Agent 决策循环，由 LLM 根据任务动态选择工具，并通过 Observation 驱动后续决策。
- 引入 Reflection 节点对最终答案进行二次校验，不足时回退到 Agent 节点重新生成，降低无依据回答。
- 参考 Hello Agents 第七章的框架思想实现 ToolRegistry、AgentState 等核心抽象，并使用 LangGraph ToolNode 负责工具执行。

## 8. 重要安全提醒

不要把真实 API Key 写进 Python 源码，也不要提交 `.env` 到 GitHub/Gitee。若某个 Key 曾经被公开，立即撤销并重新生成。
