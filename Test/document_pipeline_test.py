from pathlib import Path

from backend.rag.document_manager import DocumentManager
from backend.rag.vector_store import KnowledgeBase


def test_pipeline():

    print("================")
    print("文档处理流水线测试")
    print("================")


    # 当前项目根目录
    BASE_DIR = Path(__file__).resolve().parent.parent


    # 测试PDF路径
    pdf_path = BASE_DIR / "data" / "documents" / "product_c.pdf"


    print("\n1. PDF上传测试")
    print("----------------")

    print("测试文件:")
    print(pdf_path)


    if not pdf_path.exists():
        print("❌ PDF不存在")
        return


    manager = DocumentManager()


    result = manager.upload_and_build(
        str(pdf_path)
    )


    print("\n上传结果:")
    print(result)



    print("\n2. 向量库加载测试")
    print("----------------")


    kb = KnowledgeBase()


    loaded = kb.load()


    print(
        "向量库加载:",
        loaded
    )


    if not loaded:
        print("❌ 向量库加载失败")
        return



    print("\n3. 检索测试")
    print("----------------")


    result = kb.search_as_text(
        "产品C有哪些功能"
    )


    print(result)



    print("\n================")
    print("测试结束")
    print("================")



if __name__ == "__main__":
    test_pipeline()