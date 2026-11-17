from rag.vector_store import KnowledgeBase


kb = KnowledgeBase()

kb.load()


queries = [
    "产品C有哪些功能",
    "公司的股票激励制度是什么"
]


for q in queries:

    print("====================")
    print("问题:", q)

    results = kb.vector_store.similarity_search_with_score(
        q,
        k=3
    )

    for doc, score in results:

        print(
            "分数:",
            score,
            "| 来源:",
            doc.metadata.get("source_file")
        )

        print(
            doc.page_content[:100]
        )
