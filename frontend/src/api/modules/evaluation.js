/**
 * 评测管理 API。
 * 后端契约（backend/routers/evaluation.py）：
 *   POST /api/evaluation/run     → 202 {status:"running", total_cases}
 *                                   （已在执行中 → 409 EVALUATION_ALREADY_RUNNING）
 *   GET  /api/evaluation/results → {status:"idle|running|completed|failed",
 *                                   started_at, finished_at, error,
 *                                   summary:{total,executed,average_score,
 *                                            full_score_count,case_failed_count},
 *                                   cases:[{index,question,type,answer,
 *                                           expected_keywords,matched_keywords,
 *                                           missed_keywords,score,elapsed_ms,error}]}
 */
import request from '@/api/request'

/** 启动一次评测（后台线程执行，立即返回）。 */
export function runEvaluation() {
  return request.post('/api/evaluation/run')
}

/**
 * 获取最近一次评测状态与结果。轮询用：silent 避免轮询期间反复弹错误提示。
 */
export function getEvaluationResults() {
  return request.get('/api/evaluation/results', { silent: true })
}
