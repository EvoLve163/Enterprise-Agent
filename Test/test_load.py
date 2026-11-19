from backend.rag.vector_store import KnowledgeBase


kb = KnowledgeBase()


result = kb.load()

print("加载结果:", result)


print(
    kb.search_as_text(
        "产品C有哪些功能"
    )
)