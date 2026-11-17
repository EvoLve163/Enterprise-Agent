<template>
  <div class="eval-page">
    <!-- 操作区 -->
    <el-card shadow="never">
      <template #header>
        <div class="eval-header">
          <span><el-icon><DataAnalysis /></el-icon> 评测管理</span>
          <div class="eval-header-actions">
            <el-tag
              size="small"
              :type="statusTagType"
              effect="light"
            >
              {{ statusText }}
            </el-tag>
            <el-button
              type="primary"
              :icon="VideoPlay"
              :loading="running"
              :disabled="running"
              @click="onRun"
            >
              {{ running ? '评测执行中…' : '运行评测' }}
            </el-button>
          </div>
        </div>
      </template>

      <div class="eval-meta">
        <div>评测集：evaluation/test_cases.json（现有 {{ totalCases }} 个用例，复用 evaluation/evaluator.py 的评分逻辑）</div>
        <div v-if="results.started_at">开始时间：{{ formatDateTime(results.started_at) }}</div>
        <div v-if="results.finished_at">结束时间：{{ formatDateTime(results.finished_at) }}</div>
      </div>

      <el-alert
        v-if="running"
        type="info"
        :closable="false"
        show-icon
        class="eval-banner"
        title="评测正在后台执行：每个用例会真实调用一次 Agent（含检索与审查），预计数十秒，请勿重复提交。"
      />
      <el-alert
        v-if="results.status === 'failed' && results.error"
        type="error"
        :closable="false"
        show-icon
        class="eval-banner"
        :title="results.error"
      />

      <!-- 汇总卡片：只有真实结果到达后渲染 -->
      <div v-if="summary" class="eval-summary">
        <div class="eval-card">
          <div class="eval-card-value">{{ summary.total }}</div>
          <div class="eval-card-label">用例总数</div>
        </div>
        <div class="eval-card">
          <div class="eval-card-value">
            {{ executedText }}
          </div>
          <div class="eval-card-label">已执行</div>
        </div>
        <div class="eval-card">
          <div class="eval-card-value" :class="avgClass">{{ avgText }}</div>
          <div class="eval-card-label">平均评分（关键词命中率）</div>
        </div>
        <div class="eval-card">
          <div class="eval-card-value">{{ summary.full_score_count }} / {{ summary.executed }}</div>
          <div class="eval-card-label">满分用例</div>
        </div>
      </div>
    </el-card>

    <!-- 结果列表：来自实际执行 -->
    <el-card v-if="caseRows.length" shadow="never">
      <template #header>
        <span><el-icon><List /></el-icon> 用例结果（{{ caseRows.length }} 条，来自最近一次真实执行）</span>
      </template>

      <el-table :data="caseRows" class="eval-table" row-key="index">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="eval-expand">
              <div class="eval-expand-section">
                <div class="eval-expand-title">Agent 实际回答</div>
                <pre class="eval-answer">{{ row.answer || '（无回答）' }}</pre>
              </div>
              <div v-if="row.error" class="eval-expand-section">
                <div class="eval-expand-title">执行错误</div>
                <pre class="eval-answer eval-answer-error">{{ row.error }}</pre>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="#" width="52">
          <template #default="{ row }">{{ row.index + 1 }}</template>
        </el-table-column>
        <el-table-column label="测试问题" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.question }}</template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.type === 'knowledge' ? 'success' : 'info'" effect="plain">
              {{ row.type || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="评分" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.error" size="small" type="danger" effect="light">执行失败</el-tag>
            <el-progress
              v-else
              :percentage="Math.round(row.score * 100)"
              :status="row.score === 1 ? 'success' : row.score === 0 ? 'exception' : undefined"
              :stroke-width="12"
            />
          </template>
        </el-table-column>
        <el-table-column label="命中关键词" min-width="180">
          <template #default="{ row }">
            <div class="eval-kw">
              <el-tag
                v-for="w in row.matched_keywords"
                :key="'m-' + w"
                size="small"
                type="success"
                effect="light"
              >{{ w }}</el-tag>
              <el-tag
                v-for="w in row.missed_keywords"
                :key="'x-' + w"
                size="small"
                type="danger"
                effect="plain"
              >未命中：{{ w }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">{{ formatDuration(row.elapsed_ms) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-empty
      v-if="results.status === 'idle' && !running"
      description="尚未执行过评测。点击「运行评测」将基于 evaluation/test_cases.json 真实运行 Agent 并评分。"
    />
  </div>
</template>

<script setup>
/**
 * 评测管理页。
 * - POST /api/evaluation/run 启动（后端线程执行现有评测逻辑，409 防重复）；
 * - GET  /api/evaluation/results 轮询（running 期间每 2.5s）；
 * - 页面不执行任何 Python，不展示写死数据：没有结果就显示空态。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { DataAnalysis, List, VideoPlay } from '@element-plus/icons-vue'
import { getEvaluationResults, runEvaluation } from '@/api/modules/evaluation'
import { formatDateTime, formatDuration } from '@/utils/format'

const POLL_INTERVAL = 2500

const results = ref({
  status: 'idle',
  started_at: null,
  finished_at: null,
  error: null,
  summary: null,
  cases: null,
})
const starting = ref(false)
let pollTimer = null

const running = computed(() => results.value.status === 'running')
const summary = computed(() => results.value.summary)
const totalCases = computed(() => summary.value?.total ?? 4)
const caseRows = computed(() => results.value.cases || [])

const statusText = computed(() => {
  const map = {
    idle: '未执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败/部分失败',
  }
  return map[results.value.status] || results.value.status
})

const statusTagType = computed(() => {
  const map = { idle: 'info', running: 'primary', completed: 'success', failed: 'danger' }
  return map[results.value.status] || 'info'
})

const executedText = computed(() =>
  summary.value?.executed != null ? `${summary.value.executed} / ${summary.value.total}` : '-',
)

const avgText = computed(() =>
  summary.value?.average_score != null
    ? `${Math.round(summary.value.average_score * 100)}%`
    : '-',
)

const avgClass = computed(() => {
  const s = summary.value?.average_score
  if (s == null) return ''
  if (s >= 0.8) return 'eval-avg-good'
  if (s >= 0.5) return 'eval-avg-mid'
  return 'eval-avg-bad'
})

/* ---------- 轮询 ---------- */

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await getEvaluationResults()
      results.value = res
      if (res.status !== 'running') stopPolling()
    } catch {
      /* 轮询失败保持现状，下个周期重试 */
    }
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function refreshOnce() {
  try {
    results.value = await getEvaluationResults()
    if (results.value.status === 'running') startPolling()
  } catch {
    /* 页面初始加载失败不阻塞渲染 */
  }
}

/* ---------- 运行评测 ---------- */

async function onRun() {
  try {
    await ElMessageBox.confirm(
      `将真实执行 ${totalCases.value} 个评测用例（每个用例调用一次 Agent，含知识检索与 Reflection 审查），预计耗时数十秒。是否开始？`,
      '运行评测',
      { type: 'info', confirmButtonText: '开始评测', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  starting.value = true
  try {
    const res = await runEvaluation()
    results.value.status = 'running'
    results.value.error = null
    results.value.summary = { total: res.total_cases }
    startPolling()
  } catch {
    /* 409 等错误由 axios 拦截器 toast；刷新一次状态确认是否他人已启动 */
    await refreshOnce()
  } finally {
    starting.value = false
  }
}

onMounted(refreshOnce)
onBeforeUnmount(stopPolling)
</script>

<style scoped>
.eval-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.eval-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.eval-header > span:first-child {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.eval-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.eval-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.eval-banner {
  margin-top: 12px;
}

.eval-summary {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.eval-card {
  background: var(--ea-bg);
  border: 1px solid var(--ea-border);
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
}

.eval-card-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.3;
}

.eval-card-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.eval-avg-good { color: var(--el-color-success); }
.eval-avg-mid { color: var(--el-color-warning); }
.eval-avg-bad { color: var(--el-color-danger); }

.eval-table :deep(.el-table__expanded-cell) {
  background: var(--ea-bg);
}

.eval-expand {
  padding: 4px 8px;
}

.eval-expand-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

.eval-answer {
  margin: 0;
  padding: 10px 12px;
  max-height: 280px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.7;
  font-family: inherit;
  background: #fff;
  border: 1px solid var(--ea-border);
  border-radius: 6px;
}

.eval-answer-error {
  color: var(--el-color-danger);
}

.eval-kw {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
