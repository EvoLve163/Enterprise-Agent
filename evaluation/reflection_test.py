import sys
from pathlib import Path

# 加入项目根目录
sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)


from agent.graph import EnterpriseAgent
from core.tool_registry import ToolRegistry
from tools.knowledge import KnowledgeToolFactory
from tools.calculator import calculator
from tools.web_search import web_search

from rag.vector_store import KnowledgeBase


def run_case(agent, question):

    print("\n问题:")
    print(question)

    try:

        answer, trace = agent.ask(question)

        print("\n回答:")
        print(answer)

        print("\nTrace:")
        for item in trace:
            print(item)

        return answer, trace


    except Exception as e:

        print("\n错误:")
        print(e)

        return "", []



def test_reflection():

    print("================")
    print("Reflection 可靠性测试")
    print("================")


    # 初始化知识库

    kb = KnowledgeBase()

    if not kb.load():
        kb.build()



    # 创建工具注册中心

    registry = ToolRegistry()



    # 注册知识库工具

    knowledge_tool = KnowledgeToolFactory(kb).create()

    registry.register(knowledge_tool)



    # 注册其他工具

    registry.register(calculator)

    registry.register(web_search)



    # 获取工具

    tools = registry.tools



    # 创建Agent

    agent = EnterpriseAgent(
        tools=tools,
        max_reflections=1
    )



    cases = [

        "公司的报销流程是什么",

        "产品C有哪些功能",

        "公司有没有海外补贴政策",

        "员工退休年龄是多少",

        "住宿报销标准是多少",

        "高铁可以买什么等级",

        "你好"

    ]



    success = 0

    hallucination = 0



    for q in cases:


        answer, trace = run_case(agent,q)


        if answer:
            success += 1


        # 简单幻觉检测

        # 简单幻觉检测
        # 判断是否出现没有依据的绝对化描述

        bad_words = [
            "一定",
            "肯定",
            "全部",
            "绝对",
            "100%"
        ]

        if any(
                w in answer
                for w in bad_words
        ):
            hallucination += 1



    print("\n================")
    print("测试结果")
    print("================")


    print(
        f"Reflection通过率:{success}/{len(cases)}"
    )

    print(
        f"疑似幻觉数量:{hallucination}/{len(cases)}"
    )



if __name__ == "__main__":

    test_reflection()