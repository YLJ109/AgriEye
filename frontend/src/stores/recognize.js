import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useRecognizeStore = defineStore('recognize', () => {
  const result = ref(null)
  const loading = ref(false)
  const history = ref([])
  const historyTotal = ref(0)
  const lastQuery = ref({ page: 1, pageSize: 10, coarse: null, search: null })

  async function submit(file, { crop, plotId } = {}) {
    loading.value = true
    result.value = null
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('user_id', 1)
      if (crop) fd.append('crop', crop)
      if (plotId) fd.append('plot_id', plotId)
      result.value = await api.recognize(fd)
      return result.value
    } finally {
      loading.value = false
    }
  }

  async function loadHistory(page = 1, pageSize = 10, coarse = null, search = null) {
    lastQuery.value = { page, pageSize, coarse, search }
    const res = await api.listHistory({ user_id: 1, page, page_size: pageSize, coarse, search })
    history.value = res.items
    historyTotal.value = res.total
    return res
  }

  async function removeHistory(id) {
    await api.deleteHistory(id)
    let { page, pageSize, coarse, search } = lastQuery.value
    await loadHistory(page, pageSize, coarse, search)
    if (history.value.length === 0 && page > 1) {
      page -= 1
      await loadHistory(page, pageSize, coarse, search)
    }
  }

  return { result, loading, history, historyTotal, submit, loadHistory, removeHistory }
})