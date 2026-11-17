"""文档服务：安全校验 + 封装现有 DocumentManager 的文档管理。

并发控制：所有索引写操作（上传增量构建 / 删除重建 / 全量重建）通过
一把全局写锁串行化，避免 FAISS 并发读写与 save_local 文件竞态损坏
（Windows 下还可能遇到文件占用）。写操作期间聊天检索短暂排队。

上传文件名三重防护：Path().name 剥离目录部分 -> 拒绝 ".." 与路径分隔符
-> 白名单字符净化；用户输入无法触及 data/documents 之外的任何路径。

已知局限（一期）：add_documents 为就地修改 FAISS 对象，写入瞬间的
knowledge_search 检索存在极小竞态窗口，后续可用"重建后原子换引用"消除。
"""

import logging
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from rag.document_manager import DocumentManager

from backend.errors import BadRequestError, ConflictError, NotFoundError, UpstreamError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
_UNSAFE_CHARS = re.compile(r"[^\w\-(). \u4e00-\u9fff]")


def sanitize_upload_name(raw_name: str) -> str:
    """把上传文件名净化为安全存储文件名（xxx.pdf）；非法输入抛 400。"""
    if not raw_name or not raw_name.strip():
        raise BadRequestError(code="INVALID_FILENAME", message="文件名不能为空")
    name = Path(raw_name.replace("\\", "/")).name  # 剥离所有目录成分
    if name in {".", ".."} or not name.lower().endswith(".pdf"):
        raise BadRequestError(code="NOT_PDF", message="仅支持上传 .pdf 文件")
    stem = _UNSAFE_CHARS.sub("_", name[:-4]).strip("._")
    stem = stem[:80] or "document"
    return f"{stem}.pdf"


def validate_existing_name(filename: str) -> str:
    """校验操作用文件名：必须是纯文件名（无路径成分、无 ".."、.pdf 结尾）。"""
    name = Path((filename or "").replace("\\", "/")).name
    if (
        not name
        or name != filename
        or ".." in filename
        or not name.lower().endswith(".pdf")
    ):
        raise BadRequestError(code="INVALID_FILENAME", message="文件名不合法")
    return name


class DocumentService:
    def __init__(self, manager: DocumentManager) -> None:
        self._manager = manager
        self._kb_write_lock = threading.Lock()

    # ---------------- 只读 ----------------

    @property
    def documents_dir(self) -> Path:
        return self._manager.documents_dir

    @property
    def vector_store_loaded(self) -> bool:
        return self._manager.knowledge_base.vector_store is not None

    def list_documents(self) -> list:
        """列出知识库目录下的 PDF（现有代码无此方法，直接枚举目录实现）。"""
        docs = []
        for pdf in sorted(self.documents_dir.glob("*.pdf")):
            stat = pdf.stat()
            docs.append(
                {
                    "filename": pdf.name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime),
                }
            )
        return docs

    # ---------------- 写操作（全部持锁） ----------------

    def upload_pdf(self, raw_filename: str, data: bytes) -> dict:
        """校验并上传 PDF：落盘临时文件 -> DocumentManager.upload_and_build。"""
        safe_name = sanitize_upload_name(raw_filename)

        if not data:
            raise BadRequestError(code="EMPTY_FILE", message="上传内容为空")
        if len(data) > MAX_FILE_SIZE:
            raise BadRequestError(
                code="FILE_TOO_LARGE",
                message=f"文件过大，单个文件限制 {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )
        if not data.lstrip()[:5].startswith(b"%PDF"):
            raise BadRequestError(code="NOT_PDF", message="文件内容不是有效的 PDF 格式")

        if (self.documents_dir / safe_name).exists():
            raise ConflictError(
                code="DUPLICATE_FILENAME",
                message=f"已存在同名文件「{safe_name}」，请先删除原文件或改名后上传",
            )

        tmp_dir = None
        try:
            # DocumentManager.save_file 以传入路径的 basename 作为落盘文件名
            # （rag/document_manager.py:25），因此临时文件必须直接命名为 safe_name，
            # 否则会以随机临时名存入 documents 目录。
            tmp_dir = tempfile.mkdtemp(prefix="ea_upload_")
            tmp_path = Path(tmp_dir) / safe_name
            tmp_path.write_bytes(data)

            with self._kb_write_lock:
                # 持锁后复查同名（上传预检与获锁之间存在并发窗口）
                if (self.documents_dir / safe_name).exists():
                    raise ConflictError(
                        code="DUPLICATE_FILENAME",
                        message=f"已存在同名文件「{safe_name}」，请先删除原文件或改名后上传",
                    )
                # upload_and_build = save_file（拷贝到 documents_dir/safe_name）
                # + knowledge_base.add_document（增量加入索引），见 rag/document_manager.py:36-44
                result = self._manager.upload_and_build(str(tmp_path))
        except ConflictError:
            raise
        except Exception as exc:
            # save_file 先于索引构建执行：若 add_document 失败，文件已拷入
            # documents 目录成为孤儿文件（磁盘与索引不一致、且阻塞同名重传），
            # 必须回滚清理。此时进程内 FAISS 尚未持久化该文件的向量，无需重建。
            orphan = self.documents_dir / safe_name
            if orphan.exists():
                try:
                    orphan.unlink()
                    logger.info("已回滚清理上传失败的残留文件：%s", safe_name)
                except OSError:
                    logger.warning("回滚清理残留文件失败（需手动删除）：%s", orphan)
            logger.exception("上传并构建索引失败：%s", safe_name)
            raise UpstreamError(
                code="INDEX_BUILD_FAILED", message=f"文档解析或索引构建失败：{exc}"
            ) from exc
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        chunks = int(result.get("chunks", 0))
        return {
            "filename": result.get("file", safe_name),
            "chunks": chunks,
            "warning": (
                "该 PDF 没有可提取文本（可能为纯图片/扫描件），知识库未新增内容"
                if chunks == 0
                else None
            ),
        }

    def delete_document(self, filename: str) -> dict:
        """删除文档并重建索引（rebuild_without_file 排除该文件全量重建）。"""
        name = validate_existing_name(filename)
        if not (self.documents_dir / name).exists():
            raise NotFoundError(code="FILE_NOT_FOUND", message=f"文件不存在：{name}")
        try:
            with self._kb_write_lock:
                result = self._manager.delete_file(name)
        except Exception as exc:
            logger.exception("删除文档失败：%s", name)
            raise UpstreamError(
                code="INDEX_REBUILD_FAILED", message=f"删除并重建知识库失败：{exc}"
            ) from exc
        if not result.get("success", False):
            # DocumentManager 对不存在文件返回 {"success": False, "message": "文件不存在"}（rag/document_manager.py:49-53）
            raise NotFoundError(
                code="FILE_NOT_FOUND", message=str(result.get("message", "文件不存在"))
            )
        return {
            "success": True,
            "file": result.get("file", name),
            "remaining_chunks": int(result.get("remaining_chunks", 0)),
        }

    def rebuild(self) -> dict:
        """全量重建：重读 data/documents 下全部 PDF（rebuild_vector_store -> build）。"""
        try:
            with self._kb_write_lock:
                chunks = self._manager.rebuild_vector_store()
        except Exception as exc:
            logger.exception("知识库全量重建失败")
            raise UpstreamError(
                code="INDEX_REBUILD_FAILED", message=f"知识库重建失败：{exc}"
            ) from exc
        return {"chunks": int(chunks)}
