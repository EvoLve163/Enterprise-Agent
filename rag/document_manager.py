from pathlib import Path
import shutil

from rag.vector_store import KnowledgeBase


class DocumentManager:

    def __init__(self,documents_dir: str = "data/documents"):
        self.documents_dir = Path(documents_dir)

        self.documents_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.knowledge_base = KnowledgeBase(
            documents_dir=str(self.documents_dir)
        )


    def save_file(self,file_path: str):
        source = Path(file_path)

        target = self.documents_dir / source.name

        shutil.copy(source,target)

        return target


    def rebuild_vector_store(self):
        return self.knowledge_base.build()


    def upload_and_build(self,file_path: str):
        saved_file = self.save_file(file_path)

        count = self.knowledge_base.add_document(str(saved_file))

        return {
            "file": saved_file.name,
            "chunks": count
        }
    def delete_file(self,filename: str):

        file_path = (self.documents_dir/filename)

        if not file_path.exists():
            return {
                "success": False,
                "message": "文件不存在"
            }


        file_path.unlink()

        chunks = self.knowledge_base.rebuild_without_file(filename)


        return {
            "success": True,
            "file": filename,
            "remaining_chunks": chunks
        }