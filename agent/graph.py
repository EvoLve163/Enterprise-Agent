from typing import Annotated, TypedDict
from langchain_core.messages import (AIMessage,BaseMessage,HumanMessage,ToolMessage,)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from agent.prompts import REFLECTION_PROMPT, SYSTEM_PROMPT
from core.llm import build_llm

# _agent_node()：负责思考
# _tool_node()：负责执行工具
# _final_node()：提取答案
# _reflection_node()：检查答案
# _route_after_agent()，_route_after_reflection()：决定下一步走哪里

class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]

    question: str #用户问题

    final_answer: str #模型最终回答

    reflection_count: int #反思次数

    feedback: str #reflection给予agent反馈

    trace: list[dict] #调试日志

    tool_history: list[str] #调用工具的历史，如果需要调用的工具存在，就直接读取，不用再去重复检索去找

    status: str #表示当前状态，如果开始就是starting，调用工具就是“tool_finished"

class EnterpriseAgent:

    def __init__(self,tools: list[BaseTool],max_reflections: int = 1):
        self.llm = build_llm()
        self.tools = tools
        self.model_with_tools = self.llm.bind_tools(tools)#agent调用工具，也就是调用knowledge_search，web_search，calculator
        self.max_reflections = max_reflections
        self.graph = self._build_graph()#创建执行流程

    def _agent_node(self, state: AgentState):
        messages = list(state.get("messages", []))
        feedback = state.get("feedback", "")  #读取 Reflection反馈
        tool_history = state.get("tool_history",[]) #读取工具调用记录
        system = SYSTEM_PROMPT

        if feedback:
            system += (
                f"\n上一轮审查意见：{feedback}"
                "\n请根据意见修正回答。"
            )  #修改系统Prompt

        if tool_history:
            system += (
                "\n你已经调用过以下工具："
                f"{tool_history}"
                "\n请优先基于已有工具结果回答，"
                "不要重复调用相同工具。"
            )  #防重复工具调用

        response = self.model_with_tools.invoke([("system", system)] + messages)

        trace = list(state.get("trace", [])) #保存日志

        new_tools = list(tool_history)  #复制工具历史

        if isinstance(response, AIMessage):  #判断是不是 AIMessage

            if response.tool_calls:

                names = [call["name"] for call in response.tool_calls] #获取当前需要调用工具名字
                duplicate = [name for name in names if name in tool_history] #防重复调用工具，从历史调用工具检查

                if duplicate:
                    trace.append(
                        {
                            "node": "agent",
                            "action": "blocked_duplicate_tool",
                    #工具    "detail": duplicate
                        }
                    )

                    return {
                        "messages": [
                            AIMessage(
                                content="已有相关检索结果，请基于已有证据回答。"
                            )
                        ],
                        "trace": trace,
                        "tool_history": new_tools,
                        "status": "generating"
                    }

                new_tools.extend(names)

                trace.append(
                    {
                        "node": "agent",
                        "action": "tool_call",
                        "detail": names
                    }
                )


            else:
                trace.append(
                    {
                        "node": "agent",
                        "action": "final_answer",
                        "detail": ""
                    }
                )

        return {
            "messages": [response],
            "feedback": "",
            "trace": trace,
            "tool_history": new_tools,
            "status": "tool_calling"
            if response.tool_calls
            else "generating"
        }

    def _tool_node(self, state: AgentState):
        tool_node = ToolNode(self.tools)
        result = tool_node.invoke(state)
        return {**result,"status": "tool_finished"}
    def _final_node(self, state: AgentState):
        messages = state.get("messages", [])
        answer = ""  #存入ai回答

        for msg in reversed(messages): #reversed表示倒序，直接找AImessage效率更高
            if (isinstance(msg, AIMessage) and msg.content and not msg.tool_calls):
                answer = str(msg.content)
                break
        return {"final_answer": answer}

    def _reflection_node(self, state: AgentState):
        messages = state.get("messages", [])
        answer = "" #当前 Agent 生成的答案
        evidence_parts = []  #存放回答依据

        for msg in messages:
            if (isinstance(msg, AIMessage) and msg.content and not msg.tool_calls):
                answer = str(msg.content)

            if (isinstance(msg, ToolMessage) and msg.content):
                evidence_parts.append(str(msg.content))

        evidence = "\n\n".join(evidence_parts[-8:]) #只取最近8条依据

        prompt = (ChatPromptTemplate.from_template(REFLECTION_PROMPT).format(
                question=state.get("question", ""),
                answer=answer,
                evidence=evidence or "无工具证据"
            )
        )
        #反思机制
        review = self.llm.invoke(prompt) #调用llm判断答案质量
        review_text = str(review.content).strip() #获取审查结果 ，REVISE(需要修订)/PASS(通过)
        trace = list(state.get("trace", [])) #复制之前执行记录
        trace.append(
            {
                "node": "reflection",
                "action": ("REVISE" if review_text.startswith("REVISE:") else "PASS"),
                "detail": review_text
            }
        )

        if review_text.startswith("REVISE:"):
            count = state.get("reflection_count",0)

            return {
                "reflection_count": count + 1,
                "feedback": review_text,
                "trace": trace
            }

        return {"trace": trace}

    @staticmethod     #表示这个函数不需要访问，没有self
    def _route_after_agent(state: AgentState):
        last = state.get("messages", [])[-1] #获取最后一条消息（当前 Agent 的决定）

        if (isinstance(last, AIMessage) and last.tool_calls):
            return "tools" #告诉agent下一步去tools节点
        return "final"  #没有工具就告诉agent去final节点


    def _route_after_reflection(self, state: AgentState):  #决定Reflection之后去哪
        count = state.get("reflection_count",0) #初始化反思次数为0

        if (state.get("feedback") and count < self.max_reflections):
            return "agent"  #有需要修订的地方返回agent节点，重新回答
        return END
    # edge（边）负责控制流程
    def _build_graph(self):  #创建 LangGraph 工作流
        builder = StateGraph(AgentState) #基于 AgentState 的状态机
        builder.add_node( "agent",self._agent_node)
        builder.add_node("tools",self._tool_node)
        builder.add_node( "final",self._final_node)
        builder.add_node( "reflection",self._reflection_node)
        builder.add_edge(START,"agent") #开始调用graph后，第一个执行agent节点
        builder.add_conditional_edges("agent",self._route_after_agent,{
                "tools": "tools",
                "final": "final"
            }
        )

        builder.add_edge("tools","agent") #返回工具后还需要交给agent组织语言告诉用户
        builder.add_edge("final","reflection") #最终答案生成后进入检查
        builder.add_conditional_edges("reflection",self._route_after_reflection,{
                "agent": "agent",
                END: END
            }
        )

        return builder.compile(checkpointer=MemorySaver()) #保存Graph状态

    # 外部调用Agent的方法
    def ask(self,question: str,thread_id: str = "default"):
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=question)],
                "question": question,
                "final_answer": "",
                "reflection_count": 0,
                "feedback": "",
                "trace": [],
                "tool_history": [],
                "status": "starting"
            },
            config={"configurable": {
                    "thread_id": thread_id #相当于一个号码，区分不同用户会话
                }
            }
        )

        return (result.get("final_answer",""),
            result.get("trace",[]))