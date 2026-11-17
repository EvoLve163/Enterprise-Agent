<template>
  <div class="chat-page">
    <!-- 顶部：标题 + Agent 状态 + 会话操作 -->
    <div class="chat-toolbar">
      <div class="chat-toolbar-left">
        <h2 class="chat-title">智能问答</h2>
        <el-tag
          class="chat-status"
          :type="chatState.sending ? 'warning' : 'success'"
          effect="light"
          round
        >
          <el-icon class="status-icon" :class="{ 'is-busy': chatState.sending }">
            <Loading v-if="chatState.sending" />
            <CircleCheck v-else />
          </el-icon>
          {{ chatState.sending ? 'Agent 思考中…' : 'Agent 就绪' }}
        </el-tag>
        <el-tooltip v-if="chatState.sessionId" :content="`会话 ID：${chatState.sessionId}`" placement="bottom">
          <el-tag class="chat-status" type="info" effect="plain" round>
            会话 {{ chatState.sessionId.slice(0, 8) }}
          </el-tag>
        </el-tooltip>
      </div>

      <div class="chat-toolbar-right">
        <el-button :icon="Plus" :disabled="chatState.sending" @click="onNewSession">新建会话</el-button>
        <el-button
          type="danger"
          plain
          :icon="Delete"
          :disabled="chatState.sending || !chatState.messages.length"
          @click="onClearSession"
        >
          清空当前会话
        </el-button>
      </div>
    </div>

    <!-- 中部：消息区 -->
    <div ref="scrollRef" class="chat-messages">
      <template v-if="!chatState.messages.length">
        <div class="chat-welcome">
          <div class="welcome-icon">
            <el-icon :size="42" color="#409eff"><ChatDotRound /></el-icon>
          </div>
          <h3>你好，我是 Enterprise Agent</h3>
          <p class="welcome-desc">
            我可以查询企业知识库、联网搜索公开信息、进行精确计算，并对回答做多轮自检。
          </p>
          <div class="welcome-samples">
            <el-button
              v-for="s in samples"
              :key="s"
              size="small"
              round
              :disabled="chatState.sending"
              @click="useSample(s)"
            >
              {{ s }}
            </el-button>
          </div>
        </div>
      </template>

      <template v-else>
        <div
          v-for="msg in chatState.messages"
          :key="msg.id"
          class="msg-row"
          :class="msg.role === 'user' ? 'msg-row-user' : 'msg-row-agent'"
          :data-msg-id="msg.id"
        >
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="msg-bubble msg-bubble-user">
            <div class="msg-text">{{ msg.content }}</div>
          </div>

          <!-- Agent 消息 -->
          <template v-else>
            <div class="msg-avatar">
              <el-icon :size="20" color="#fff"><Cpu /></el-icon>
            </div>
            <div
              class="msg-bubble msg-bubble-agent"
              :class="`assistant-msg assistant-${msg.status}`"
            >
              <!-- 加载中 -->
              <div v-if="msg.status === 'loading'" class="msg-loading">
                <span class="loading-dot"></span>
                <span class="loading-dot"></span>
                <span class="loading-dot"></span>
                <span class="loading-text">Agent 正在思考…</span>
              </div>

              <!-- 失败 -->
              <div v-else-if="msg.status === 'error'" class="msg-error">
                <el-alert type="error" :closable="false" show-icon :title="msg.error || '请求失败'" />
                <el-button size="small" type="primary" plain :icon="RefreshRight" @click="retryFailed">
                  重试
                </el-button>
              </div>

              <!-- 正常回答 -->
              <template v-else>
                <div class="md-body msg-text" v-html="renderedAnswer(msg)"></div>
                <CitationList :citations="citationsOf(msg)" />
                <TraceTimeline v-if="msg.trace && msg.trace.length" :trace="msg.trace" :elapsed-ms="msg.elapsedMs" />
              </template>
            </div>
          </template>
        </div>
      </template>
    </div>

    <!-- 底部：输入区 -->
    <div class="chat-input">
      <el-input
        ref="inputRef"
        v-model="draft"
        type="textarea"
        resize="none"
        :rows="3"
        :maxlength="2000"
        show-word-limit
        placeholder="输入问题，Enter 发送，Shift + Enter 换行"
        class="chat-input-box"
        @keydown="onKeydown"
      />
      <div class="chat-input-actions">
        <span class="input-hint">连续对话共享上下文 · 回答含执行轨迹与引用来源</span>
        <el-button
          type="primary"
          size="large"
          :icon="Promotion"
          :loading="chatState.sending"
          :disabled="!draft.trim()"
          class="send-btn"
          @click="send"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 智能问答页：全部问答经 Axios POST /api/chat 走后端 EnterpriseAgent，
 * 前端不直接调用任何大模型 API。
 */
import { nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  CircleCheck,
  Cpu,
  Delete,
  Loading,
  Plus,
  Promotion,
  RefreshRight,
} from '@element-plus/icons-vue'
import { chatState, retryFailed, resetSession, sendMessage } from '@/store/chatSession'
import { renderMarkdown } from '@/utils/markdown'
import { extractCitations } from '@/utils/citations'
import TraceTimeline from '@/components/TraceTimeline.vue'
import CitationList from '@/components/CitationList.vue'

const draft = ref('')
const scrollRef = ref(null)
const inputRef = ref(null)

const samples = [
  '公司差旅报销的制度是什么？',
  '请介绍一下产品C',
  '用计算器计算 1234 * 567 + 8901',
  '搜索 DeepSeek 最新发布的模型',
]

function useSample(s) {
  draft.value = s
  nextTick(() => inputRef.value?.focus())
}

function renderedAnswer(msg) {
  return renderMarkdown(msg.content)
}

function citationsOf(msg) {
  return extractCitations(msg.content)
}

function send() {
  const text = draft.value.trim()
  if (!text) return
  if (chatState.sending) return
  draft.value = ''
  sendMessage(text)
}

/** Enter 发送；Shift+Enter 换行（默认行为）；中文输入法组词确认时不发送 */
function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

async function onNewSession() {
  await resetSession()
  ElMessage.success('已开启新会话')
}

async function onClearSession() {
  await resetSession()
  ElMessage.success('当前会话已清空')
}

/* 新消息 / 回答更新时滚动到底部 */
watch(
  () => chatState.messages.map((m) => `${m.id}:${m.status}:${m.content.length}`).join('|'),
  async () => {
    await nextTick()
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  },
)
</script>

<style>
/* v-html 渲染的 Markdown 正文（作用于子元素，不能 scoped） */
.md-body {
  font-size: 14px;
  line-height: 1.7;
  color: var(--el-text-color-primary);
  word-break: break-word;
  overflow-wrap: anywhere;
}

.md-body > :first-child {
  margin-top: 0;
}

.md-body > :last-child {
  margin-bottom: 0;
}

.md-body p {
  margin: 8px 0;
}

.md-body h1,
.md-body h2,
.md-body h3,
.md-body h4 {
  margin: 14px 0 8px;
  font-weight: 600;
  line-height: 1.4;
}

.md-body h1 {
  font-size: 18px;
}

.md-body h2 {
  font-size: 16px;
}

.md-body h3 {
  font-size: 15px;
}

.md-body ul,
.md-body ol {
  margin: 8px 0;
  padding-left: 22px;
}

.md-body li {
  margin: 4px 0;
}

.md-body blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--ea-primary);
  background: var(--ea-bg);
  color: var(--el-text-color-regular);
}

.md-body code {
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
  background: var(--ea-bg);
  border: 1px solid var(--ea-border);
  border-radius: 3px;
  padding: 1px 5px;
}

.md-body pre {
  margin: 10px 0;
  border-radius: 6px;
  overflow: hidden;
}

.md-body pre code {
  display: block;
  padding: 12px 14px;
  overflow-x: auto;
  background: #1e1e2e;
  border: none;
  color: #cdd6f4;
  line-height: 1.6;
  white-space: pre;
}

.md-body table {
  border-collapse: collapse;
  margin: 10px 0;
  width: 100%;
  font-size: 13px;
}

.md-body th,
.md-body td {
  border: 1px solid var(--ea-border);
  padding: 6px 10px;
  text-align: left;
}

.md-body th {
  background: var(--ea-bg);
  font-weight: 600;
}

.md-body a {
  color: var(--ea-primary);
  text-decoration: none;
}

.md-body a:hover {
  text-decoration: underline;
}

.md-body hr {
  border: none;
  border-top: 1px solid var(--ea-border);
  margin: 12px 0;
}
</style>

<style scoped>
.chat-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
  border: 1px solid var(--ea-border);
  border-radius: 8px;
  overflow: hidden;
}

/* 顶部工具栏 */
.chat-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--ea-border);
  background: #fff;
}

.chat-toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.chat-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.chat-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.status-icon.is-busy {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.chat-toolbar-right {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 消息区 */
.chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.chat-welcome {
  margin: auto;
  text-align: center;
  max-width: 520px;
  padding: 30px 0;
}

.welcome-icon {
  margin-bottom: 12px;
}

.chat-welcome h3 {
  margin: 0 0 8px;
  font-size: 20px;
}

.welcome-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.7;
  margin: 0 0 18px;
}

.welcome-samples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

/* 消息行 */
.msg-row {
  display: flex;
  gap: 10px;
  max-width: 100%;
}

.msg-row-user {
  justify-content: flex-end;
}

.msg-row-agent {
  justify-content: flex-start;
}

.msg-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #7c3aed);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.msg-bubble {
  max-width: min(78%, 900px);
  border-radius: 10px;
  padding: 12px 16px;
  min-width: 0;
}

.msg-bubble-user {
  background: var(--ea-primary);
  color: #fff;
  border-top-right-radius: 2px;
}

.msg-bubble-user .msg-text {
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-bubble-agent {
  background: var(--ea-bg);
  border: 1px solid var(--ea-border);
  border-top-left-radius: 2px;
}

/* 加载态 */
.msg-loading {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 0;
}

.loading-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ea-primary);
  animation: bounce 1.2s ease-in-out infinite;
}

.loading-dot:nth-child(2) {
  animation-delay: 0.15s;
}

.loading-dot:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

.loading-text {
  margin-left: 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

/* 失败态 */
.msg-error {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

/* 输入区 */
.chat-input {
  flex-shrink: 0;
  border-top: 1px solid var(--ea-border);
  padding: 14px 20px 12px;
  background: #fff;
}

.chat-input-box :deep(.el-textarea__inner) {
  font-size: 14px;
  line-height: 1.6;
}

.chat-input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}

.input-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* 窄屏适配 */
@media (max-width: 768px) {
  .msg-bubble {
    max-width: 92%;
  }

  .chat-toolbar {
    flex-wrap: wrap;
  }
}
</style>
