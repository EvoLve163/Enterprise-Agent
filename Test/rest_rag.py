from agent.rag.vector_store import KnowledgeBase


kb = KnowledgeBase()


count = kb.add_document(
    "data/documents/product_c.pdf"
)


print(
    "新增chunk数量:",
    count
)


result = kb.search_as_text(
    "产品C有哪些功能"
)


print(result)