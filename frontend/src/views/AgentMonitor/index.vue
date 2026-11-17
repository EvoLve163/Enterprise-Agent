<template>
  <div class="monitor-page">
    <!-- 数据源选择 -->
    <el-card shadow="never" class="monitor-source-card">
      <div class="monitor-source">
        <el-radio-group v-model="source" @change="onSourceChange">
          <el-radio-button value="local">本机会话（当前聊天）</el-radio-button>
          <el-radio-button value="remote">按会话 ID 查询</el-radio-button>
        </el-radio-group>

        <div v-if="source === 'remote'" class="monitor-remote">
          <el-input
            v-model="remoteSessionId"
            placeholder="输入 session_id（见智能问答页会话标识）"
            clearable
            class="monitor-session-input"
            @keyup.enter="loadRemote"
          />
          <el-button type="primary" :loading="remoteLoading" @click="loadRemote">查询</el-button>
        </div>
        <div v-else class="monitor-local-hint">
          当前会话 <span class="monitor-session-id">{{ chatState.sessionId || '（新会话，未提问）' }}</span>
          ，共 {{ localRounds.length }} 轮对话
        </div>
      </div>
      <div class="monitor-note">
        说明：后端 trace 不含"任务开始/结束"显式条目，此处以<strong>用户提问</strong>作为每轮执行起点，
        之后按真实发生顺序展示工具调用、最终回答与 Reflection 审查；未发生的步骤不会出现。
      </div>
    </el-card>

    <!-- 会话查询结果 -->
    <el-alert
      v-if="remoteError"
      type="error"
      :title="remoteError"
      :closable="false"
      show-icon
      class="monitor-alert"
    />

    <!-- 执行轮次列表 -->
    <template v-if="activeRounds.length">
      <el-card
        v-for="round in activeRounds"
        :key="round.key"
        shadow="never"
        class="monitor-round"
      >
        <template #header>
          <div class="monitor-round-header">
            <el-tag size="small" type="info" effect="plain">第 {{ round.no }} 轮</el-tag>
            <span class="monitor-question" :title="round.question">{{ round.question }}</span>
            <div class="monitor-round-badges">
              <el-tag v-if="round.toolCount" size="small" type="warning" effect="light">
                工具 × {{ round.toolCount }}
              </el-tag>
              <el-tag
                v-if="round.reflection"
                size="small"
                :type="round.reflection === 'PASS' ? 'success' : 'danger'"
                effect="light"
              >
                Reflection {{ round.reflection === 'PASS' ? '通过' : '修订' }}
              </el-tag>
              <el-tag v-if="round.revisedCount" size="small" type="warning" effect="plain">
                修订 × {{ round.revisedCount }}
              </el-tag>
              <el-tag v-if="round.status === 'loading'" size="small" type="primary" effect="light">
                <el-icon class="is-loading"><Loading /></el-icon> 执行中
              </el-tag>
              <el-tag v-else-if="round.status === 'error'" size="small" type="danger" effect="light">
                执行失败
              </el-tag>
              <span v-if="round.elapsedMs != null" class="monitor-elapsed">
                {{ formatDuration(round.elapsedMs) }}
              </span>
            </div>
          </div>
        </template>

        <!-- 执行中占位 -->
        <div v-if="round.status === 'loading'" class="monitor-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          Agent 正在执行……
        </div>

        <!-- 失败态 -->
        <el-alert
          v-else-if="round.status === 'error'"
          type="error"
          :title="round.error || '本轮执行失败'"
          :closable="false"
          show-icon
        />

        <template v-else>
          <!-- 执行轨迹（真实 trace 数据） -->
          <TraceTimeline :trace="round.trace" :elapsed-ms="round.elapsedMs" />

          <!-- 执行结果：最终回答 -->
          <div class="monitor-answer">
            <div class="monitor-answer-title" @click="toggleAnswer(round.key)">
              <el-icon>
                <component :is="isAnswerOpen(round.key) ? ArrowDown : ArrowRight" />
              </el-icon>
              执行结果 · 最终回答
              <span class="monitor-answer-length">{{ round.answer.length }} 字</span>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-show="isAnswerOpen(round.key)" class="md-body monitor-answer-body" v-html="round.answerHtml" />
          </div>
        </template>
      </el-card>
    </template>

    <!-- 空状态 -->
    <el-empty
      v-else-if="source === 'local' && !chatState.sending"
      description="当前会话暂无对话记录。前往「智能问答」发起提问后，此处将展示真实执行轨迹。"
    />
    <el-empty
      v-else-if="source === 'remote' && remoteLoaded && !remoteRounds.length"
      description="该会话存在但没有带执行轨迹的回复记录。"
    />
  </div>
</template>

<script setup>
/**
 * Agent 执行监控页。
 * 数据源全部真实：
 *  1. 本机会话 —— chatSession store（与智能问答页共享，SPA 内切换不丢失）；
 *  2. 会话查询 —— GET /api/sessions/{id}/history（服务侧记录，assistant 轮带 trace）。
 * 不伪造步骤：trace 中没有的节点（如显式的"开始执行"）不会出现；
 * 以用户提问作为每轮起点，其余按 trace 真实条目渲染（复用 TraceTimeline）。
 */
import { computed, ref } from 'vue'
import { ArrowDown, ArrowRight, Loading } from '@element-plus/icons-vue'
import TraceTimeline from '@/components/TraceTimeline.vue'
import { chatState } from '@/store/chatSession'
import { getSessionHistory } from '@/api/modules/chat'
import { renderMarkdown } from '@/utils/markdown'
import { formatDuration } from '@/utils/format'

const source = ref('local')
const remoteSessionId = ref('')
const remoteLoading = ref(false)
const remoteLoaded = ref(false)
const remoteError = ref('')
const remoteRounds = ref([])

/* ---------- 本机会话：按 user→assistant 配对成轮次 ---------- */

function pairRounds(messages, keyPrefix) {
  const rounds = []
  let pendingQuestion = ''
  let no = 0
  for (const m of messages) {
    if (m.role === 'user') {
      pendingQuestion = m.content
    } else if (m.role === 'assistant') {
      no += 1
      const trace = Array.isArray(m.trace) ? m.trace : []
      const reflectionEntries = trace.filter((e) => e?.node === 'reflection')
      rounds.push({
        key: `${keyPrefix}-${no}`,
        no,
        question: pendingQuestion || '（未记录提问）',
        answer: m.content || '',
        answerHtml: renderMarkdown(m.content || ''),
        trace,
        elapsedMs: m.elapsedMs ?? null,
        status: m.status || 'done',
        error: m.error || '',
        toolCount: trace.reduce(
          (acc, e) => acc + (e?.action === 'tool_call' && Array.isArray(e.detail) ? e.detail.length : 0),
          0,
        ),
        reflection: reflectionEntries.length
          ? reflectionEntries[reflectionEntries.length - 1].action
          : '',
        revisedCount: reflectionEntries.filter((e) => e.action === 'REVISE').length,
      })
      pendingQuestion = ''
    }
  }
  /* 正在执行的一轮（已提问、尚无回复） */
  if (keyPrefix === 'local' && pendingQuestion) {
    rounds.push({
      key: `${keyPrefix}-running`,
      no: no + 1,
      question: pendingQuestion,
      answer: '',
      answerHtml: '',
      trace: [],
      elapsedMs: null,
      status: 'loading',
      error: '',
      toolCount: 0,
      reflection: '',
      revisedCount: 0,
    })
  }
  return rounds
}

const localRounds = computed(() => pairRounds(chatState.messages, 'local'))
const activeRounds = computed(() =>
  source.value === 'local' ? localRounds.value : remoteRounds.value,
)

/* ---------- 执行结果展开状态（rounds 是 computed 返回的普通对象，
   突变其字段不具响应式，因此用组件级 Set 管理） ---------- */

const expandedAnswers = ref(new Set())

function isAnswerOpen(key) {
  return expandedAnswers.value.has(key)
}

function toggleAnswer(key) {
  const next = new Set(expandedAnswers.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  expandedAnswers.value = next
}

/* ---------- 会话查询 ---------- */

function onSourceChange() {
  remoteError.value = ''
}

async function loadRemote() {
  const id = remoteSessionId.value.trim()
  if (!id) {
    remoteError.value = '请输入 session_id'
    return
  }
  remoteLoading.value = true
  remoteError.value = ''
  remoteRounds.value = []
  try {
    const res = await getSessionHistory(id)
    remoteLoaded.value = true
    remoteRounds.value = pairRounds(
      (res.messages || []).map((m) => ({
        role: m.role,
        content: m.content,
        trace: m.trace || [],
        status: 'done',
        error: '',
        elapsedMs: null,
      })),
      'remote',
    )
  } catch (err) {
    remoteLoaded.value = false
    remoteError.value = err?.message || '查询失败'
  } finally {
    remoteLoading.value = false
  }
}
</script>

<style scoped>
.monitor-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.monitor-source {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.monitor-remote {
  display: flex;
  gap: 8px;
  flex: 1;
  min-width: 320px;
  justify-content: flex-end;
}

.monitor-session-input {
  max-width: 420px;
}

.monitor-session-id {
  font-family: Consolas, Monaco, monospace;
  color: var(--el-text-color-secondary);
}

.monitor-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.monitor-alert {
  margin: 0;
}

.monitor-round-header {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.monitor-question {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.monitor-round-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.monitor-elapsed {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.monitor-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  padding: 12px 0;
}

.is-loading {
  animation: monitor-rotate 1s linear infinite;
}

@keyframes monitor-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.monitor-answer {
  margin-top: 10px;
  border-top: 1px dashed var(--ea-border);
  padding-top: 8px;
}

.monitor-answer-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  cursor: pointer;
  user-select: none;
}

.monitor-answer-length {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.monitor-answer-body {
  margin-top: 8px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid var(--ea-border);
  border-radius: 6px;
  max-height: 360px;
  overflow-y: auto;
}
</style>
