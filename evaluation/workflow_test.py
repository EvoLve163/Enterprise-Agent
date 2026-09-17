import json
from pathlib import Path

from agent.graph import EnterpriseAgent

from rag.vector_store import KnowledgeBase

from tools.knowledge import KnowledgeToolFactory
from tools.calculator import calculator
from tools.web_search import web_search



def load_cases():

    path = Path(__file__).parent / "workflow_cases.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def build_agent():

    # 初始化知识库
    kb = KnowledgeBase()

    # 创建知识库检索工具
    knowledge_search = KnowledgeToolFactory(kb).create()


    tools = [
        knowledge_search,
        calculator,
        web_search
    ]


    agent = EnterpriseAgent(
        tools=tools,
        max_reflections=1
    )


    return agent



def check_tools(trace, expected_tools):

    """
    根据Agent trace判断是否调用正确工具
    """

    used_tools = []


    for item in trace:

        if item.get("action") == "tool_call":

            used_tools.extend(
                item.get("detail", [])
            )


    return all(
        tool in used_tools
        for tool in expected_tools
    )



def run_test():

    cases = load_cases()

    agent = build_agent()


    success = 0


    for index, case in enumerate(cases, 1):

        question = case["question"]

        expected_tools = case["expected_tools"]


        print("\n============================")
        print(f"测试 {index}")
        print("问题:")
        print(question)


        try:

            answer, trace = agent.ask(
                question,
                thread_id=f"workflow_test_{index}"
            )


            print("\n回答:")
            print(answer)


            print("\n执行轨迹:")
            for item in trace:
                print(item)



            if check_tools(
                trace,
                expected_tools
            ):

                success += 1
                print("\n结果: ✅成功")


            else:

                print("\n结果: ❌工具调用错误")



        except Exception as e:

            print("\n结果: ❌运行失败")
            print(e)



    rate = success / len(cases)


    print("\n============================")
    print(
        f"工作流一次成功率: {rate:.2%}"
    )



if __name__ == "__main__":

    run_test()