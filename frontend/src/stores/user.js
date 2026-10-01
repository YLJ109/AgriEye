import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { getToken, setToken, clearToken } from '@/api'

export const useUserStore = defineStore('user', () => {
  const token = ref(getToken())
  const user = ref(null)            // { id, username, nickname, role, region, avatar }
  const stats = ref(null)
  const systemInfo = ref(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)
  // 兼容旧代码里直接读 userId 的写法
  const userId = computed(() => user.value?.id ?? 0)
  const nickname = computed(() => user.value?.nickname || '农户')
  const categoryStats = computed(() => stats.value?.by_category || {})

  async function loadSystemInfo() {
    try { systemInfo.value = await api.systemInfo() } catch { /* ignore */ }
  }

  async function loadStats() {
    if (!isAuthenticated.value) return
    loading.value = true
    try { stats.value = await api.systemStats() } catch { /* ignore */ }
    finally { loading.value = false }
  }

  /** 登录：后端校验口令并返回 JWT */
  async function login(username, password) {
    const data = await api.login(username, password)
    setToken(data.access_token)
    token.value = data.access_token
    user.value = data.user
    await loadStats()
    return data.user
  }

  /** 注册：成功后直接签发令牌，免二次登录 */
  async function register(payload) {
    const data = await api.register(payload)
    setToken(data.access_token)
    token.value = data.access_token
    user.value = data.user
    await loadStats()
    return data.user
  }

  /** 刷新页面后：用本地 token 换回身份，token 失效则清空 */
  async function restore() {
    if (!token.value) return false
    try {
      user.value = await api.me()
      return true
    } catch {
      clearToken()
      token.value = ''
      user.value = null
      return false
    }
  }

  function logout() {
    api.logout().catch(() => {})   // 无状态 JWT，失败也不影响本地清理
    clearToken()
    token.value = ''
    user.value = null
    stats.value = null
  }

  return {
    token, user, stats, systemInfo, loading,
    isAuthenticated, userId, nickname, categoryStats,
    loadSystemInfo, loadStats, login, register, restore, logout,
  }
})
