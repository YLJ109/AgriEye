import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/', timeout: 30000 })

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const silent = err.config?.silent
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
  // 系统
  systemInfo: () => http.get('/api/system/info', { silent: true }),
  systemStats: (userId = 1) => http.get('/api/system/stats', { params: { user_id: userId }, silent: true }),

  // 识别
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

  // 历史
  listHistory: (params) => http.get('/api/history/list', { params, silent: true }),
  getHistoryDetail: (id) => http.get(`/api/history/detail/${id}`),
  deleteHistory: (id) => http.delete(`/api/history/${id}`),


  // AI 对话（智谱 GLM）
  chatCompletions: (data) => http.post('/api/chat/completions', data),
  chatModels: () => http.get('/api/chat/models', { silent: true }),

  // 农事
  solarTerms: () => http.get('/api/farming/solar-terms', { silent: true }),
  currentAdvice: (crop) => http.get('/api/farming/current-advice', { params: { crop }, silent: true }),
  listReminders: (userId = 1) => http.get('/api/farming/reminders', { params: { user_id: userId }, silent: true }),
  createReminder: (data) => http.post('/api/farming/reminders', data),
  toggleReminder: (id) => http.patch(`/api/farming/reminders/${id}/done`),
  deleteReminder: (id) => http.delete(`/api/farming/reminders/${id}`),
}

export default api