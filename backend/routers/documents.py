"""知识库文档管理路由。"""

import logging

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from backend.deps import get_document_service
from backend.schemas import (
    DocumentDeletedResponse,
    DocumentListResponse,
    RebuildResponse,
    UploadResponse,
)
from backend.services.document_service import DocumentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """获取知识库 PDF 文档列表（文件名、大小、最后修改时间）。"""
    docs = service.list_documents()
    return DocumentListResponse(total=len(docs), documents=docs)


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="要上传的 PDF 文件（单文件限制 20MB）"),
    service: DocumentService = Depends(get_document_service),
) -> UploadResponse:
    """上传 PDF 并增量加入向量知识库，对进行中的会话立即生效。

    校验链：文件名净化（防路径穿越）-> 非空 -> 大小上限 -> PDF 魔数
    -> 重名拒绝（409）-> 索引构建（失败不影响现有知识库）。

    阻塞的解析/向量化工作通过 run_in_threadpool 在线程池执行，
    不阻塞事件循环。
    """
    try:
        data = await file.read()
        result = await run_in_threadpool(service.upload_pdf, file.filename or "", data)
    finally:
        await file.close()
    return UploadResponse(**result)


@router.delete("/{filename}", response_model=DocumentDeletedResponse)
def delete_document(
    filename: str,
    service: DocumentService = Depends(get_document_service),
) -> DocumentDeletedResponse:
    """删除指定文档并触发知识库重建（移除该文档对应的向量）。"""
    return DocumentDeletedResponse(**service.delete_document(filename))


@router.post("/rebuild", response_model=RebuildResponse)
def rebuild(
    service: DocumentService = Depends(get_document_service),
) -> RebuildResponse:
    """全量重建知识库：重读 data/documents 下所有 PDF（索引修复 / 手动放置文件后使用）。"""
    return RebuildResponse(**service.rebuild())
