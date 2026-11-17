/** 健康检查 */
import request from '@/api/request'

/** GET /api/health（silent：状态探测失败不弹全局错误提示） */
export function getHealth() {
  return request.get('/api/health', { silent: true })
}
