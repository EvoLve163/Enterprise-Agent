import json
from pathlib import Path

from agent.graph import EnterpriseAgent
from tools.knowledge import KnowledgeToolFactory
from tools.calculator import calculator
from tools.web_search import web_search
from rag.vector_store import KnowledgeBase


def load_cases():

    path = Path(__file__).parent / "tool_cases.json"

    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)



def test_tool():

    kb = KnowledgeBase()
    kb.load()

    knowledge_tool = KnowledgeToolFactory(kb).create()


    tools = [
        knowledge_tool,
        web_search,
        calculator
    ]


    agent = EnterpriseAgent(
        tools=tools
    )


    cases = load_cases()


    success = 0


    for i,case in enumerate(cases,1):

        print("================")
        print("测试",i)
        print(case["question"])


        answer,trace = agent.ask(
            case["question"]
        )


        print(trace)


        called = "none"


        for item in trace:

            if item["action"] == "tool_call":

                called = item["detail"][0]


        print(
            "实际:",
            called
        )

        print(
            "期望:",
            case["expected_tool"]
        )


        if called == case["expected_tool"]:
            success += 1
            print("✅")
        else:
            print("❌")


    print("================")
    print(
        f"工具选择正确率:{success}/{len(cases)}={success/len(cases)*100:.2f}%"
    )


if __name__=="__main__":
    test_tool()