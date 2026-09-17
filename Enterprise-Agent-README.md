# Enterprise Agent

> 基于 LangGraph + LangChain + RAG 的企业智能知识与业务助手

Enterprise Agent 是一个基于Hello Agents学习项目中丰富的agent从0到1的知识而创造的面向企业知识场景的大语言模型 Agent 系统。
项目结合 RAG 检索增强、工具调用、状态化工作流与 Reflection 机制，
实现企业文档理解、业务问题分析以及智能问答能力。

------------------------------------------------------------------------

## ✨ 项目特点

-   基于 LangGraph 构建状态化 Agent 工作流
-   基于 RAG 构建企业知识库问答能力
-   支持 Agent 自主选择工具完成任务
-   引入 Reflection 机制提升回答可靠性
-   支持多轮对话与知识库管理
-   提供自动化 Evaluation 评测体系

------------------------------------------------------------------------

## 🏗️ 系统架构

    User
     |
     v
    Agent Controller
     |
     +----------------+
     |                |
     v                v
    RAG              Tools
     |                |
    FAISS        Web Search
     |            Calculator
    Knowledge
     |
     v
    Answer Generation
     |
     v
    Reflection Check
     |
     v
    Final Response

------------------------------------------------------------------------

## 🚀 核心能力

### 1. 企业知识库 RAG

支持企业文档处理流程：

    PDF
     |
    Document Loader
     |
    Text Splitter
     |
    Embedding
     |
    FAISS Vector Store
     |
    Retriever
     |
    LLM Answer

实现：

-   PDF 文档解析
-   文本切分
-   向量化存储
-   相似度检索
-   基于知识来源生成回答

------------------------------------------------------------------------

### 2. Agent 工具调用

Agent 根据用户任务动态选择工具：

  Tool               功能
  ------------------ ----------------
  Knowledge Search   企业知识库检索
  Web Search         外部信息查询
  Calculator         数学计算

示例：

用户：

    今年销售额相比去年增长多少？

Agent：

    分析任务
        ↓
    调用 Calculator
        ↓
    生成结果

------------------------------------------------------------------------

### 3. LangGraph 状态工作流

采用 Agent Loop：

    Agent
     |
    Decision
     |
    Tool
     |
    Observation
     |
    Agent
     |
    Answer

通过 State 管理：

-   对话历史
-   当前任务
-   工具结果
-   执行状态

------------------------------------------------------------------------

### 4. Reflection 自检机制

加入答案反思节点：

    Answer
      |
    Reflection
      |
      +---- 满足要求 -> 输出
      |
      +---- 信息不足 -> Agent重新处理

用于：

-   检查回答完整性
-   降低幻觉
-   提高复杂问题稳定性

------------------------------------------------------------------------

## 📊 Evaluation

建立自动化测试体系，对典型业务问题进行评估。

  测试场景       Accuracy
  -------------- ----------
  报销流程查询   1.0
  产品 A 问答    1.0
  身份规则查询   1.0
  产品 C 问答    0.33

平均准确率：

    0.83

低分案例用于分析：

-   知识覆盖不足
-   检索召回不足
-   文档切片优化方向

------------------------------------------------------------------------

## 🛠️ 技术栈

### LLM

-   DeepSeek API
-   OpenAI Compatible API

### Agent

-   LangGraph
-   LangChain

### RAG

-   FAISS
-   Embedding Model
-   RecursiveCharacterTextSplitter

### UI

-   Streamlit

### Language

-   Python

------------------------------------------------------------------------

## 📂 项目结构

    Enterprise-Agent

    ├── agent
    │   ├── graph.py
    │   ├── prompts.py
    │   └── state.py
    │
    ├── rag
    │   ├── retriever.py
    │   └── embedding.py
    │
    ├── tools
    │   ├── search.py
    │   └── calculator.py
    │
    ├── evaluation
    │   └── evaluate.py
    │
    ├── app.py
    ├── cli.py
    └── requirements.txt

------------------------------------------------------------------------

## ⚙️ 快速开始

### 安装依赖

``` bash
python -m venv .venv

# Windows
.venv\\Scripts\\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

------------------------------------------------------------------------

### 配置环境变量

复制：

    .env.example -> .env

填写：

    OPENAI_API_KEY=
    OPENAI_BASE_URL=
    MODEL_NAME=

注意：

不要将真实 API Key 提交到 GitHub。

------------------------------------------------------------------------

### 添加知识库

将企业 PDF 放入：

    data/documents/

------------------------------------------------------------------------

### 启动

CLI：

``` bash
python cli.py
```

Web：

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## 🎯 示例场景

### 企业制度查询

    公司的报销流程是什么？

Agent 自动：

    检索知识库
          ↓
    获取相关文档
          ↓
    生成答案

------------------------------------------------------------------------

### 数据计算

    今年收入1280万，去年1000万，同比增长多少？

Agent：

    调用 Calculator
          ↓
    计算增长率
          ↓
    返回结果

------------------------------------------------------------------------

## 🔒 Security

请勿提交：

-   `.env`
-   API Key
-   企业私有文档
-   本地向量数据库文件

建议使用：

    .env.example

提供配置模板。

------------------------------------------------------------------------

## 📄 License

MIT License
