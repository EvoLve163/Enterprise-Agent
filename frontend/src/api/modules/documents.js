/** 知识库文档管理 API（第三阶段接入页面） */
import request from '@/api/request'

/** GET /api/documents */
export function listDocuments() {
  return request.get('/api/documents')
}

/**
 * POST /api/documents/upload（multipart/form-data，字段名 file）
 * @param {File} file
 * @param {{onUploadProgress?: Function}} [opts] axios 配置（上传进度等）
 * @returns {Promise<{ filename: string, chunks: number, warning: string|null }>}
 */
export function uploadDocument(file, opts = {}) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: opts.onUploadProgress,
  })
}

/** DELETE /api/documents/{filename} */
export function deleteDocument(filename) {
  return request.delete(`/api/documents/${encodeURIComponent(filename)}`)
}

/** POST /api/documents/rebuild */
export function rebuildKnowledge() {
  return request.post('/api/documents/rebuild')
}
