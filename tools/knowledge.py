from langchain.tools import tool
from rag.vector_store import KnowledgeBase


class KnowledgeToolFactory:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def create(self):
        kb = self.kb

        @tool("knowledge_search")
        def knowledge_search(query: str) -> str:
            """Search the enterprise private knowledge base.

            Use this tool when the user asks about internal company documents,
            policies, product manuals, processes, FAQs, or uploaded PDFs.
            Returns passages with source file and page information.
            """
            return kb.search_as_text(query)

        return knowledge_search
