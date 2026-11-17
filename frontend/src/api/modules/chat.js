/** 聊天与会话 API（第三阶段接入页面） */
import request from '@/api/request'

/**
 * POST /api/chat
 * @param {{ question: string, session_id?: string }} data
 * @returns {Promise<{ session_id: string, answer: string, trace: Array<{node:string,action:string,detail?:any}>, elapsed_ms: number }>}
 */
export function askChat(data) {
  return request.post('/api/chat', data)
}

/**
 * GET /api/sessions/{sessionId}/history
 * @returns {Promise<{ session_id: string, count: number, messages: Array<{role:string,content:string,trace:Array|null,created_at:string}> }>}
 */
export function getSessionHistory(sessionId) {
  return request.get(`/api/sessions/${sessionId}/history`)
}

/** DELETE /api/sessions/{sessionId} */
export function deleteSession(sessionId) {
  return request.delete(`/api/sessions/${sessionId}`)
}
