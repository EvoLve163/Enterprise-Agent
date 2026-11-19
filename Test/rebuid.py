from agent.rag.vector_store import KnowledgeBase


kb = KnowledgeBase()

kb.load()

print(
    "向量数量:",
    len(kb.vector_store.index_to_docstore_id)
)


for doc_id in kb.vector_store.index_to_docstore_id.values():

    doc = kb.vector_store.docstore.search(doc_id)

    print(
        "来源:",
        doc.metadata.get("source_file")
    )


print("\n测试产品C:")

print(
    kb.search_as_text(
        "产品C有哪些功能"
    )
)