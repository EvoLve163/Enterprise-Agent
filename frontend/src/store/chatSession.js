/**
 * 聊天会话状态（模块级单例）。
 * 状态放在模块作用域而非组件内：切换路由（知识库/监控页）再回来，
 * 当前会话的消息记录不丢失。
 *
 * 与后端契约一致（POST /api/chat）：
 *   请求 {question, session_id?} → 响应 {session_id, answer, trace, elapsed_ms}
 */
import { reactive } from 'vue'
import { askChat, deleteSession } from '@/api/modules/chat'

let msgSeq = 0

export const chatState = reactive({
  /** 当前后端会话 id（thread_id）；null 表示新会话，首次提问由后端生成 */
  sessionId: null,
  /** @type {Array<{id:number, role:'user'|'assistant', content:string, trace:Array, elapsedMs:number, status:'done'|'loading'|'error', error:string, pendingQuestion:string, createdAt:number}>} */
  messages: [],
  sending: false,
})

/**
 * 发送问题。发送中重复调用直接忽略（防重复提交）。
 * @param {string} question 用户问题原文
 */
export async function sendMessage(question) {
  const text = (question || '').trim()
  if (!text || chatState.sending) return

  chatState.messages.push({
    id: ++msgSeq,
    role: 'user',
    content: text,
    status: 'done',
    createdAt: Date.now(),
  })

  const placeholder = reactive({
    id: ++msgSeq,
    role: 'assistant',
    content: '',
    trace: [],
    elapsedMs: null,
    status: 'loading',
    error: '',
    pendingQuestion: text,
    createdAt: Date.now(),
  })
  chatState.messages.push(placeholder)

  chatState.sending = true
  try {
    const body = { question: text }
    if (chatState.sessionId) body.session_id = chatState.sessionId
    const res = await askChat(body)

    chatState.sessionId = res.session_id
    placeholder.content = res.answer || ''
    placeholder.trace = Array.isArray(res.trace) ? res.trace : []
    placeholder.elapsedMs = res.elapsed_ms ?? null
    placeholder.status = 'done'
  } catch (err) {
    placeholder.status = 'error'
    placeholder.error = err?.message || '请求失败，请稍后重试'
    placeholder.pendingQuestion = text
  } finally {
    chatState.sending = false
  }
}

/**
 * 重试上一条失败的消息：移除失败气泡并重发原问题。
 */
export function retryFailed() {
  const idx = chatState.messages.findIndex((m) => m.status === 'error')
  if (idx === -1) return
  const q = chatState.messages[idx].pendingQuestion
  chatState.messages.splice(idx, 1)
  sendMessage(q)
}

/**
 * 重置会话：新建会话 / 清空当前会话共用。
 * 尽力通知后端释放会话记录（服务侧 LRU）；随后本地清空并换新会话 id。
 * 注意：LangGraph MemorySaver 检查点在服务进程内常驻，因此必须换新的
 * session_id 才能保证新会话不携带旧上下文。
 */
export async function resetSession() {
  if (chatState.sending) return
  const old = chatState.sessionId
  chatState.messages = []
  chatState.sessionId = null
  if (old) {
    try {
      await deleteSession(old)
    } catch {
      /* 静默：后端会话不存在等情况不影响前端重置 */
    }
  }
}
