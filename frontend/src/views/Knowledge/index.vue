<template>
  <div class="kb-page">
    <!-- 概览卡片 -->
    <div class="kb-overview">
      <div class="kb-card">
        <div class="kb-card-icon kb-icon-doc"><el-icon :size="22"><Collection /></el-icon></div>
        <div class="kb-card-body">
          <div class="kb-card-value">{{ list.total }}</div>
          <div class="kb-card-label">文档数量</div>
        </div>
      </div>

      <div class="kb-card">
        <div class="kb-card-icon kb-icon-store"><el-icon :size="22"><Box /></el-icon></div>
        <div class="kb-card-body">
          <div class="kb-card-value kb-value-text">
            <el-tag :type="health.vector_store_loaded ? 'success' : 'danger'" effect="light" size="small">
              {{ health.vector_store_loaded ? '已加载' : '未加载' }}
            </el-tag>
          </div>
          <div class="kb-card-label">知识库 / 向量索引</div>
        </div>
      </div>

      <div class="kb-card">
        <div class="kb-card-icon kb-icon-chunk"><el-icon :size="22"><Grid /></el-icon></div>
        <div class="kb-card-body">
          <div class="kb-card-value kb-value-text">
            <template v-if="lastKnownChunks !== null">{{ lastKnownChunks }} 块</template>
            <el-tooltip v-else content="执行上传 / 删除 / 重建操作后，此处显示后端返回的向量块数" placement="top">
              <span class="kb-muted">待操作后显示</span>
            </el-tooltip>
          </div>
          <div class="kb-card-label">向量块（最近一次操作后）</div>
        </div>
      </div>

      <div class="kb-card">
        <div class="kb-card-icon" :class="lastOp.ok ? 'kb-icon-ok' : 'kb-icon-fail'">
          <el-icon :size="22"><Clock /></el-icon>
        </div>
        <div class="kb-card-body">
          <div class="kb-card-value kb-value-text kb-op-text" :title="lastOp.text">
            {{ lastOp.text }}
          </div>
          <div class="kb-card-label">最近操作（本次会话）</div>
        </div>
      </div>
    </div>

    <!-- 上传区 -->
    <el-card shadow="never" class="kb-upload-card">
      <template #header>
        <div class="kb-card-header">
          <span><el-icon><Upload /></el-icon> 上传文档（PDF，≤ 20MB）</span>
          <span class="kb-header-hint">上传后自动加入向量索引，智能问答立即生效</span>
        </div>
      </template>

      <el-upload
        drag
        accept=".pdf,application/pdf"
        :show-file-list="false"
        :auto-upload="false"
        :multiple="false"
        :disabled="uploading"
        :on-change="onFileChange"
        class="kb-uploader"
      >
        <div class="kb-upload-zone" :class="{ 'is-dragover': false }">
          <el-icon :size="40" color="#409eff"><UploadFilled /></el-icon>
          <div class="kb-upload-title">将 PDF 拖拽到此处，或点击选择文件</div>
          <div class="kb-upload-sub">仅支持 PDF · 单文件不超过 20MB · 同名文件将被拒绝（409）</div>
        </div>
      </el-upload>

      <div v-if="uploading || uploadPercent > 0" class="kb-upload-progress">
        <el-progress
          :percentage="uploadPercent"
          :status="uploadStatus === 'error' ? 'exception' : uploadStatus === 'success' ? 'success' : undefined"
          :stroke-width="10"
        />
        <div class="kb-upload-status">
          <template v-if="uploadStatus === 'uploading'">
            <el-icon class="is-loading"><Loading /></el-icon> 正在上传 {{ uploadFileName }}…
          </template>
          <template v-else-if="uploadStatus === 'building'">
            <el-icon class="is-loading"><Loading /></el-icon>
            上传完成，服务端正在解析并构建向量索引…
          </template>
          <template v-else-if="uploadStatus === 'success'">
            <el-icon color="#67c23a"><CircleCheck /></el-icon>
            {{ uploadFileName }} 已入库：新增 {{ uploadResult.chunks }} 个向量块
            <span v-if="uploadResult.warning" class="kb-warning">（{{ uploadResult.warning }}）</span>
          </template>
          <template v-else-if="uploadStatus === 'error'">
            <el-icon color="#f56c6c"><CircleClose /></el-icon> {{ uploadError }}
          </template>
        </div>
      </div>
    </el-card>

    <!-- 文档列表 -->
    <el-card shadow="never" class="kb-list-card">
      <template #header>
        <div class="kb-card-header">
          <span><el-icon><Files /></el-icon> 文档列表（{{ list.total }}）</span>
          <div class="kb-header-actions">
            <el-button size="small" :icon="Refresh" :loading="listLoading" @click="refreshAll">刷新</el-button>
            <el-button
              size="small"
              type="warning"
              plain
              :icon="RefreshRight"
              :loading="rebuilding"
              :disabled="uploading || listLoading"
              @click="onRebuild"
            >
              重建知识库
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="listLoading"
        :data="list.documents"
        empty-text="知识库暂无文档，请上传 PDF"
        class="kb-table"
      >
        <el-table-column label="文件名" min-width="280">
          <template #default="{ row }">
            <div class="kb-file-cell">
              <el-icon :size="18" color="#409eff"><Document /></el-icon>
              <span class="kb-filename" :title="row.filename">{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
        </el-table-column>

        <el-table-column label="修改时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.modified_at) }}</template>
        </el-table-column>

        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" :icon="View" @click="openDetail(row)">详情</el-button>
            <el-button
              size="small"
              text
              type="danger"
              :icon="Delete"
              :loading="deletingFilename === row.filename"
              :disabled="deletingFilename !== null && deletingFilename !== row.filename"
              @click="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 文档详情对话框 -->
    <el-dialog v-model="detail.visible" :title="detail.doc?.filename || '文档详情'" width="480px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="文件名">{{ detail.doc?.filename }}</el-descriptions-item>
        <el-descriptions-item label="大小">{{ formatBytes(detail.doc?.size_bytes || 0) }}</el-descriptions-item>
        <el-descriptions-item label="最后修改时间">{{ formatDateTime(detail.doc?.modified_at) }}</el-descriptions-item>
      </el-descriptions>
      <el-alert
        class="kb-detail-note"
        type="info"
        :closable="false"
        show-icon
        title="在线预览 PDF 原文需要文件服务接口，当前后端未提供；可先通过智能问答检索其内容。"
      />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 知识库管理页。
 * 全部操作走后端现有接口（契约见 backend/routers/documents.py）：
 *   GET  /api/documents                → {total, documents:[{filename,size_bytes,modified_at}]}
 *   POST /api/documents/upload         → 201 {filename, chunks, warning?}
 *   DELETE /api/documents/{filename}   → {success, file, remaining_chunks}
 *   POST /api/documents/rebuild        → {chunks}
 * 一致性策略：任何操作完成后都重新拉取列表；删除/上传/重建的向量块数
 * 来自后端真实返回值（不前端估算）；失败（非 2xx）由 axios 拦截器抛错，
 * 页面只在成功分支更新状态 —— 重建失败不会误报成功。
 */
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Box,
  CircleCheck,
  CircleClose,
  Clock,
  Collection,
  Delete,
  Document,
  Files,
  Grid,
  Loading,
  Refresh,
  RefreshRight,
  Upload,
  UploadFilled,
  View,
} from '@element-plus/icons-vue'
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  rebuildKnowledge,
} from '@/api/modules/documents'
import { getHealth } from '@/api/modules/health'
import { formatBytes, formatDateTime } from '@/utils/format'

const MAX_SIZE = 20 * 1024 * 1024

/* 概览状态 */
const list = reactive({ total: 0, documents: [] })
const health = reactive({ vector_store_loaded: false, document_count: 0 })
const lastKnownChunks = ref(null)
const lastOp = reactive({ text: '暂无操作', ok: true })
const listLoading = ref(false)

/* 上传状态 */
const uploading = ref(false)
const uploadPercent = ref(0)
const uploadStatus = ref('') // '' | uploading | building | success | error
const uploadFileName = ref('')
const uploadError = ref('')
const uploadResult = reactive({ chunks: 0, warning: '' })

/* 删除 / 重建状态 */
const deletingFilename = ref(null)
const rebuilding = ref(false)

/* 详情对话框 */
const detail = reactive({ visible: false, doc: null })

function markOp(ok, text) {
  lastOp.ok = ok
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  lastOp.text = `${time} ${text}`
}

async function refreshAll() {
  listLoading.value = true
  try {
    const [docRes, healthRes] = await Promise.all([
      listDocuments(),
      getHealth().catch(() => null),
    ])
    list.total = docRes.total
    list.documents = docRes.documents || []
    if (healthRes) Object.assign(health, healthRes)
  } finally {
    listLoading.value = false
  }
}

/* ---------- 上传 ---------- */

function onFileChange(file) {
  const raw = file.raw
  if (!raw) return
  doUpload(raw)
}

async function doUpload(file) {
  if (uploading.value) return

  /* 本地预检（后端仍会完整校验） */
  if (!/\.pdf$/i.test(file.name)) {
    uploadStatus.value = 'error'
    uploadError.value = '仅支持 PDF 文件'
    uploadPercent.value = 100
    return
  }
  if (file.size > MAX_SIZE) {
    uploadStatus.value = 'error'
    uploadError.value = `文件超过 20MB 上限（当前 ${formatBytes(file.size)}）`
    uploadPercent.value = 100
    return
  }

  uploading.value = true
  uploadStatus.value = 'uploading'
  uploadFileName.value = file.name
  uploadError.value = ''
  uploadPercent.value = 0
  try {
    const res = await uploadDocument(file, {
      onUploadProgress(e) {
        if (e.total) uploadPercent.value = Math.round((e.loaded / e.total) * 100)
        if (uploadPercent.value >= 100) uploadStatus.value = 'building'
      },
    })
    uploadStatus.value = 'success'
    uploadPercent.value = 100
    uploadResult.chunks = res.chunks
    uploadResult.warning = res.warning || ''
    /* 后端只返回新增块数：已知基线才累加，未知则留待删除/重建给出权威总数 */
    if (lastKnownChunks.value !== null) lastKnownChunks.value += res.chunks
    markOp(true, `上传 ${res.filename}（+${res.chunks} 块）`)
    ElMessage.success(`上传成功：已加入 ${res.chunks} 个向量块`)
    await refreshAll()
  } catch (err) {
    uploadStatus.value = 'error'
    uploadError.value = err?.message || '上传失败'
    markOp(false, `上传 ${file.name} 失败：${uploadError.value}`)
  } finally {
    uploading.value = false
  }
}

/* ---------- 删除（二次确认） ---------- */

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.filename}」吗？该文档将从磁盘移除，其向量也将从知识库索引中清除，删除后无法通过智能问答检索到其内容。`,
      '删除文档',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return /* 用户取消 */
  }

  deletingFilename.value = row.filename
  try {
    const res = await deleteDocument(row.filename)
    lastKnownChunks.value = res.remaining_chunks
    markOp(true, `删除 ${res.file}（剩 ${res.remaining_chunks} 块）`)
    ElMessage.success(`已删除 ${res.file}，知识库剩余 ${res.remaining_chunks} 个向量块`)
    await refreshAll()
  } catch (err) {
    markOp(false, `删除 ${row.filename} 失败：${err?.message || '未知错误'}`)
  } finally {
    deletingFilename.value = null
  }
}

/* ---------- 全量重建 ---------- */

async function onRebuild() {
  try {
    await ElMessageBox.confirm(
      '将重新读取 data/documents 下全部 PDF 并重建向量索引（可修复索引异常）。文档较多时耗时较长，期间请勿执行其他操作。',
      '重建知识库',
      { type: 'warning', confirmButtonText: '开始重建', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  rebuilding.value = true
  try {
    const res = await rebuildKnowledge()
    lastKnownChunks.value = res.chunks
    markOp(true, `重建完成（共 ${res.chunks} 块）`)
    ElMessage.success(`知识库重建完成，共 ${res.chunks} 个向量块`)
    await refreshAll()
  } catch (err) {
    markOp(false, `重建失败：${err?.message || '未知错误'}`)
  } finally {
    rebuilding.value = false
  }
}

/* ---------- 详情 ---------- */

function openDetail(row) {
  detail.doc = row
  detail.visible = true
}

onMounted(refreshAll)
</script>

<style scoped>
.kb-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* 概览卡片 */
.kb-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px;
}

.kb-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border: 1px solid var(--ea-border);
  border-radius: 8px;
  padding: 14px 16px;
}

.kb-card-icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kb-icon-doc {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.kb-icon-store {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.kb-icon-chunk {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.kb-icon-ok {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.kb-icon-fail {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.kb-card-body {
  min-width: 0;
}

.kb-card-value {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.3;
}

.kb-value-text {
  font-size: 14px;
}

.kb-card-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.kb-muted {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

.kb-op-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
}

/* 卡片头 */
.kb-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.kb-card-header > span:first-child {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.kb-header-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.kb-header-actions {
  display: flex;
  gap: 8px;
}

/* 上传区 */
.kb-uploader :deep(.el-upload-dragger) {
  padding: 28px 20px;
  border-radius: 8px;
}

.kb-upload-title {
  margin-top: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.kb-upload-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.kb-upload-progress {
  margin-top: 12px;
}

.kb-upload-status {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.is-loading {
  animation: kb-rotate 1s linear infinite;
}

@keyframes kb-rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.kb-warning {
  color: var(--el-color-warning);
}

/* 列表 */
.kb-file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.kb-filename {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}

.kb-detail-note {
  margin-top: 14px;
}
</style>
