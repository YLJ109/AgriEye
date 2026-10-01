import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useUserStore = defineStore('user', () => {
  const userId = ref(1)
  const nickname = ref('农户')
  const stats = ref(null)
  const systemInfo = ref(null)
  const loading = ref(false)

  async function loadSystemInfo() {
    try { systemInfo.value = await api.systemInfo() } catch { /* ignore */ }
  }

  async function loadStats() {
    loading.value = true
    try { stats.value = await api.systemStats(userId.value) } catch { /* ignore */ }
    finally { loading.value = false }
  }

  const categoryStats = computed(() => stats.value?.by_category || {})

  return { userId, nickname, stats, systemInfo, loading, categoryStats, loadSystemInfo, loadStats }
})