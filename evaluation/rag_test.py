from pathlib import Path
import json

from rag.vector_store import KnowledgeBase



def load_cases():

    path = Path(__file__).parent / "rag_cases.json"

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def test_rag():

    cases = load_cases()


    kb = KnowledgeBase()


    # 加载已有FAISS向量库
    loaded = kb.load()


    if not loaded:

        print(
            "❌ FAISS向量库不存在，请先执行知识库构建"
        )

        return



    hit_count = 0

    valid_count = 0


    irrelevant_query_count = 0

    irrelevant_doc_count = 0



    print("========================")
    print("RAG 检索评测")
    print("========================")



    for index, case in enumerate(cases,1):

        query = case["query"]

        expected = case["expected"]



        print("\n------------------------")
        print(f"测试 {index}")

        print("问题:")
        print(query)



        # 使用你的真实RAG检索流程
        docs = kb.search(
            query,
            k=5
        )



        sources = []


        for doc in docs:

            source = doc.metadata.get(
                "source_file",
                ""
            )

            sources.append(source)



        print("\n召回:")

        for source in sources:
            print(source)



        # =====================
        # 正向命中测试
        # =====================

        if expected:


            valid_count += 1


            success = any(
                expected in source
                for source in sources
            )


            if success:

                hit_count += 1

                print(
                    "结果: ✅命中"
                )

            else:

                print(
                    "结果: ❌未命中"
                )



        # =====================
        # 无关查询测试
        # =====================

        else:


            irrelevant_query_count += 1


            if docs:

                irrelevant_doc_count += len(docs)


                print(
                    "结果: ⚠️召回内容"
                )

            else:

                print(
                    "结果: ✅成功过滤"
                )



    print("\n========================")



    hit_rate = (
        hit_count / valid_count
        if valid_count
        else 0
    )


    print(
        f"Top-K命中率: "
        f"{hit_count}/{valid_count}"
        f" = {hit_rate:.2%}"
    )



    print(
        f"无关查询召回文档数: "
        f"{irrelevant_doc_count}"
    )


    print("========================")



if __name__ == "__main__":

    test_rag()