from backend.rag.vector_store import KnowledgeBase


kb = KnowledgeBase()


kb.load()


print("删除前:")

print(
    kb.search_as_text(
        "产品C有哪些功能"
    )
)


count = kb.rebuild_without_file(
    "product_c.pdf"
)


print(
    "\n重建完成，剩余chunk:",
    count
)


print("\n删除后:")

print(
    kb.search_as_text(
        "产品C有哪些功能"
    )
)