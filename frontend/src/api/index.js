import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/', timeout: 30000 })

// ---------- 令牌读写（SEC-001/002：令牌由后端签发，前端只负责携带与清除）----------
const TOKEN_KEY = 'agrieye_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem('isLogin')   // 清理旧版遗留的伪登录标记
  localStorage.removeItem('username')
}

// ---------- 请求拦截：统一携带 Bearer token ----------
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ---------- 响应拦截：401 统一登出并跳登录 ----------
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const silent = err.config?.silent
    if (err.response?.status === 401) {
      clearToken()
      // 只在非登录页时跳转，避免登录失败时的重复跳转
      if (!window.location.pathname.startsWith('/login')) {
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }
    if (!silent) {
      if (!err.response) {
        ElMessage.error('网络连接失败，请检查网络或服务是否启动')
      } else {
        const msg = err.response?.data?.detail || err.message || '请求失败'
        ElMessage.error(msg)
      }
    }
    return Promise.reject(err)
  }
)

export const api = {
  // 认证
  login: (username, password) => http.post('/api/auth/login', { username, password }),
  register: (data) => http.post('/api/auth/register', data),
  me: () => http.get('/api/auth/me', { silent: true }),
  logout: () => http.post('/api/auth/logout', null, { silent: true }),

  // 系统
  systemInfo: () => http.get('/api/system/info', { silent: true }),
  systemStats: () => http.get('/api/system/stats', { silent: true }),

  // 识别（user_id 由后端按 token 判定，不再由前端传入）
  recognize: (formData, onProgress) =>
    http.post('/api/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    }),
  getDiagnosis: (id) => http.get(`/api/recognize/${id}`),
  storeDiagnosis: (formData) => http.post('/api/recognize/store', formData),

  // RAG 问答
  askAdvisor: (question, crop, context) =>
    http.post('/api/rag/ask', { question, crop, top_k: 5, context }),
  searchKnowledge: (q) => http.get('/api/rag/search', { params: { q, top_k: 5 } }),

  // 历史（search 下沉后端，支持跨页搜索 —— FUNC-001）
  listHistory: (params) => http.get('/api/history/list', { params, silent: true }),
  getHistoryDetail: (id) => http.get(`/api/history/detail/${id}`),
  deleteHistory: (id) => http.delete(`/api/history/${id}`),
  listPlots: () => http.get('/api/history/plots', { silent: true }),
  createPlot: (data) => http.post('/api/history/plots', data),

  // AI 对话（智谱 GLM）
  chatCompletions: (data) => http.post('/api/chat/completions', data),
  chatModels: () => http.get('/api/chat/models', { silent: true }),

  // 农事
  solarTerms: () => http.get('/api/farming/solar-terms', { silent: true }),
  currentAdvice: (crop) => http.get('/api/farming/current-advice', { params: { crop }, silent: true }),
  listReminders: () => http.get('/api/farming/reminders', { silent: true }),
  createReminder: (data) => http.post('/api/farming/reminders', data),
  toggleReminder: (id) => http.patch(`/api/farming/reminders/${id}/done`),
  deleteReminder: (id) => http.delete(`/api/farming/reminders/${id}`),
}

export default api
