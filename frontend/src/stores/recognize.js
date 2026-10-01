import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useRecognizeStore = defineStore('recognize', () => {
  const result = ref(null)
  const loading = ref(false)
  const history = ref([])
  const historyTotal = ref(0)
  // FUNC-002：分页与筛选状态收归 store，页面切换/返回后不丢失，也不再散落在组件里
  const page = ref(1)
  const pageSize = ref(12)
  const coarse = ref(null)
  const search = ref(null)
  const lastQuery = ref({ page: 1, pageSize: 12, coarse: null, search: null })

  async function submit(file, { crop, plotId } = {}) {
    loading.value = true
    result.value = null
    try {
      const fd = new FormData()
      fd.append('file', file)
      // 归属由后端按 token 判定，不传 user_id（SEC-002）
      if (crop) fd.append('crop', crop)
      if (plotId) fd.append('plot_id', plotId)
      result.value = await api.recognize(fd)
      return result.value
    } finally {
      loading.value = false
    }
  }

  async function loadHistory(nextPage = page.value, nextPageSize = pageSize.value,
                             nextCoarse = coarse.value, nextSearch = search.value) {
    // 搜索/筛选条件变化时必须回到第一页，否则会停在一个超出范围的空页上
    if (nextSearch !== search.value || nextCoarse !== coarse.value) nextPage = 1
    page.value = nextPage
    pageSize.value = nextPageSize
    coarse.value = nextCoarse
    search.value = nextSearch
    lastQuery.value = { page: nextPage, pageSize: nextPageSize, coarse: nextCoarse, search: nextSearch }
    const res = await api.listHistory({
      page: nextPage, page_size: nextPageSize, coarse: nextCoarse, search: nextSearch,
    })
    history.value = res.items
    historyTotal.value = res.total
    return res
  }

  async function removeHistory(id) {
    await api.deleteHistory(id)
    const { page: p, pageSize: ps, coarse: c, search: s } = lastQuery.value
    await loadHistory(p, ps, c, s)
    // 删掉当前页最后一条时自动回退一页，避免停在空白页
    if (history.value.length === 0 && p > 1) {
      await loadHistory(p - 1, ps, c, s)
    }
  }

  return {
    result, loading, history, historyTotal,
    page, pageSize, coarse, search, lastQuery,
    submit, loadHistory, removeHistory,
  }
})