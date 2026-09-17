from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import EMBEDDING_MODEL, TOP_K


class KnowledgeBase:
    def __init__(self, documents_dir: str = "data/documents"):
        # PDF文档目录
        BASE_DIR = Path(__file__).resolve().parent.parent
        self.documents_dir = BASE_DIR / documents_dir
        # FAISS向量库存储目录,文件夹路径
        self.vector_store_dir = BASE_DIR / "data/vector_store"

        # //保存内存中的FAISS向量数据库对象
        self.vector_store: Optional[FAISS] = None

        # Embedding模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL, #问题，为什么用这个模型
            encode_kwargs={"normalize_embeddings": True},
        )

    def build(self) -> int:
        pdf_files = sorted(self.documents_dir.glob("*.pdf"))
        if not pdf_files:
            self.vector_store = None
            return 0

        documents = []
        for pdf in pdf_files:
            loader = PyPDFLoader(str(pdf))#PDF加载
            pages = loader.load()#读取PDF
            for page in pages:
                page.metadata.update(
                    {
                        "source_file": pdf.name,
                        "document_type": "company_policy",
                        "page_number": page.metadata.get("page", 0) + 1,
                    }
                ) #保存额外信息，给这一页打上“它来自哪个 PDF”的标签
            #把当前 PDF 的所有页面，加入总的 documents 列表
            documents.extend(pages)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, #每个文本块大约 800 个字符。
            chunk_overlap=120, #相邻两个文本块重叠 120 个字符。
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        )
        # 把每个文本块转换成向量
        chunks = splitter.split_documents(documents)
        #建立向量数据库
        self.vector_store = FAISS.from_documents(chunks,self.embeddings)

        # 保存向量数据库
        self.vector_store_dir.mkdir(
            exist_ok=True,
            parents=True
        )

        self.vector_store.save_local(
            str(self.vector_store_dir)
        )

        return len(chunks)

    def add_document(self, pdf_path: str) -> int:
        pdf = Path(pdf_path)

        if not pdf.exists():
            return 0

        loader = PyPDFLoader(str(pdf))
        pages = loader.load()

        for page in pages:
            page.metadata.update(
                {
                    "source_file": pdf.name,
                    "document_type": "company_policy",
                    "page_number": page.metadata.get("page", 0) + 1,
                }
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "；",
                " ",
                ""
            ],
        )

        chunks = splitter.split_documents(pages)

        if self.vector_store is None:
            self.load()

        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vector_store.add_documents(chunks)

        self.vector_store.save_local(
            str(self.vector_store_dir)
        )

        return len(chunks)
        # k表示返回几个最相关的文本块
    def rebuild_without_file(self, filename: str) -> int:
        documents = []

        pdf_files = sorted(
            self.documents_dir.glob("*.pdf")
        )

        for pdf in pdf_files:

            if pdf.name == filename:
                continue

            loader = PyPDFLoader(
                str(pdf)
            )

            pages = loader.load()

            for page in pages:
                page.metadata.update(
                    {
                        "source_file": pdf.name,
                        "document_type": "company_policy",
                        "page_number": page.metadata.get("page", 0) + 1,
                    }
                )

            documents.extend(
                pages
            )


        if not documents:
            self.vector_store = None
            return 0


        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "；",
                " ",
                ""
            ],
        )

        chunks = splitter.split_documents(documents)

        self.vector_store = FAISS.from_documents(chunks,self.embeddings)


        self.vector_store.save_local(str(self.vector_store_dir))
        return len(chunks)

    def rebuild(self):
        return self.build()
    def search(self, query: str, k: int = TOP_K):
        """
        带相似度阈值的检索

        query: 用户问题

        k: 最大返回数量的相关文本块

        score_threshold:文档（pdf）最低相关度分数
        """

        if self.vector_store is None:
            return []
                                    #根据用户问题，在向量数据库里面寻找最相似的文本，并返回相似度分数
        docs = self.vector_store.max_marginal_relevance_search(
            query,
            k=k,
            fetch_k=10
        )
        return docs

    # 用 FAISS 找和用户问题最相似的 K 个文本块**优化成分数机制，分数高返回，低则返回空

    def search_as_text(self, query: str, k: int = TOP_K) -> str:
        docs = self.search(query, k=k)
        if not docs:
            return "知识库暂无可用内容。"

        lines = []
        for i, doc in enumerate(docs, start=1):
            source = doc.metadata.get("source_file","未知文档" )
            page = doc.metadata.get("page_number", "未知页码")
            lines.append(
                f"[依据{i}] 来源：{source}，第{page}页\n"
                f"{doc.page_content.strip()}"
            )

        return "\n\n".join(lines)

    def load(self):
        if self.vector_store_dir.exists():
            self.vector_store = FAISS.load_local(
                str(self.vector_store_dir),
                self.embeddings,
                allow_dangerous_deserialization=True
            )

            return True

        return False