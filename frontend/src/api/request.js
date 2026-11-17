/**
 * Axios 统一封装
 *
 * - baseURL 来自环境变量 VITE_API_BASE_URL（.env.development / .env.production）
 * - 超时 300s：聊天接口涉及多轮 LLM + 工具调用，耗时较长
 * - 响应拦截：正常响应直接解包 data；错误统一归一化为
 *   Error{ code, status, message } 并弹出提示（config.silent = true 时不弹）
 * - 后端错误契约：{"detail": {"code": "...", "message": "..."}}
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 300000,
})

request.interceptors.request.use((config) => config)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    let code = 'NETWORK_ERROR'
    let message = '网络异常，请检查后端服务是否已启动'

    if (error.code === 'ECONNABORTED') {
      code = 'TIMEOUT'
      message = '请求超时，请稍后重试'
    } else if (error.response) {
      const detail = error.response.data && error.response.data.detail
      if (detail && typeof detail === 'object') {
        code = detail.code || `HTTP_${error.response.status}`
        message = detail.message || `请求失败（HTTP ${error.response.status}）`
      } else {
        code = `HTTP_${error.response.status}`
        message = `请求失败（HTTP ${error.response.status}）`
      }
    }

    const silent = error.config && error.config.silent
    if (!silent) {
      ElMessage.error(message)
    }

    return Promise.reject(
      Object.assign(new Error(message), {
        code,
        status: error.response ? error.response.status : undefined,
      })
    )
  }
)

export default request
