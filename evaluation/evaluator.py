import json
from pathlib import Path

from agent.graph import EnterpriseAgent
from tools.calculator import calculator
from tools.knowledge import KnowledgeToolFactory
from tools.web_search import web_search
from core.tool_registry import ToolRegistry
from rag.vector_store import KnowledgeBase


def load_cases():

    path = Path(__file__).parent / "test_cases.json"

    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)


def build_agent():

    kb = KnowledgeBase()

    if not kb.load():
        kb.build()

    knowledge_tool = KnowledgeToolFactory(kb).create()

    registry = ToolRegistry()

    for tool in (
        knowledge_tool,
        web_search,
        calculator
    ):
        registry.register(tool)

    return EnterpriseAgent(
        registry.tools
    )



def evaluate_answer(
        answer,
        keywords
):

    score = 0

    for word in keywords:

        if word in answer:
            score += 1


    return score / len(keywords)



def run():

    agent = build_agent()

    cases = load_cases()


    total_score = 0


    for case in cases:

        print("="*50)

        print(
            "问题:",
            case["question"]
        )


        answer, trace = agent.ask(
            case["question"]
        )


        score = evaluate_answer(
            answer,
            case["expected_keywords"]
        )


        total_score += score


        print(
            "答案:",
            answer[:200]
        )


        print(
            "评分:",
            score
        )


    final_score = (
        total_score / len(cases)
    )


    print("="*50)

    print(
        "平均准确率:",
        round(final_score,2)
    )



if __name__ == "__main__":
    run()