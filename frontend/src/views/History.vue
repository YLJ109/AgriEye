<script setup>
import { ref, onMounted, onActivated, computed, watch } from 'vue'
import api from '@/api'
import { useRecognizeStore } from '@/stores/recognize'
import { useUserStore } from '@/stores/user'
import StatCard from '@/components/StatCard.vue'
import CategoryBadge from '@/components/CategoryBadge.vue'
import ConfidenceRing from '@/components/ConfidenceRing.vue'
import DetectionCanvas from '@/components/DetectionCanvas.vue'
import EmptyState from '@/components/EmptyState.vue'
import Skeleton from '@/components/Skeleton.vue'
import { RefreshCw, Trash2, Eye, Search } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useRecognizeStore()
const userStore = useUserStore()
// FUNC-002：分页/筛选状态收归 store，返回本页时保留在第几页、搜了什么
const page = computed({
  get: () => store.page,
  set: (v) => { store.page = v },
})
const pageSize = computed({
  get: () => store.pageSize,
  set: (v) => { store.pageSize = v },
})
const filterCoarse = ref('')
const search = ref('')
const dateRange = ref([])
const sortBy = ref('time')
const detailVisible = ref(false)
const detail = ref(null)
const loading = ref(false)

const coarseOptions = [
  { value: '', label: '全部类别' },
  { value: 'fungal_disease', label: '真菌病害' },
  { value: 'pest', label: '虫害' },
  { value: 'deficiency', label: '土壤缺肥' },
  { value: 'phytotoxicity', label: '农药药害' },
]
const sortOptions = [
  { value: 'time', label: '按时间倒序' },
  { value: 'time-asc', label: '按时间正序' },
  { value: 'confidence', label: '按置信度' },
]
const SEV = { mild: { label: '轻度', type: 'success' }, moderate: { label: '中度', type: 'warning' }, severe: { label: '重度', type: 'danger' } }

const filteredItems = computed(() => {
  let list = store.history.slice()
  // 关键词搜索
  if (search.value) {
    const kw = search.value
    list = list.filter(h => (h.fine_label || h.coarse_label || '').includes(kw))
  }
  // 日期范围筛选
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    const s = new Date(start).getTime()
    const e = new Date(end).getTime() + 86400000
    list = list.filter(h => {
      const t = new Date(h.created_at).getTime()
      return t >= s && t <= e
    })
  }
  // FUNC-004：排序已下沉到后端 SQL（listHistory 的 sort 参数）。
  // 前端只保留日期区间筛选；若仍在这里排序，排的只是当前页的 12 条。
  return list
})

function onThumbError(e) {
  const img = e.target
  img.style.display = 'none'
  const ph = document.createElement('div')
  ph.className = 'thumb-placeholder'
  ph.textContent = '图片加载失败'
  img.parentNode.appendChild(ph)
}

async function load() {
  loading.value = true
  try {
    // FUNC-004：把排序维度一起交给后端
    await store.loadHistory(page.value, pageSize.value, filterCoarse.value || null,
                            search.value || null, sortBy.value || 'time')
  } finally { loading.value = false }
}
async function viewDetail(id) { detail.value = await api.getHistoryDetail(id); detailVisible.value = true }
async function remove(id) {
  try {
    await ElMessageBox.confirm('确定删除该诊断记录？', '提示', { type: 'warning' })
  } catch { return }
  await store.removeHistory(id); ElMessage.success('已删除')
}
// FUNC-004：排序/筛选条件变化后必须重新请求后端，否则改了排序但数据没变
watch([sortBy, filterCoarse], () => load())

onMounted(() => { load(); userStore.loadStats() })
/* 被 KeepAlive 缓存后，onMounted 只在首次进入时执行一次；
   每次重新进入页面时重新拉取，避免看到过期记录（列表数据需要新鲜，页面筛选/页码状态仍保留） */
let actCount = 0
onActivated(() => { actCount += 1; if (actCount > 1) { load(); userStore.loadStats() } })
</script>

<template>
  <div class="page">
    <!-- 统计 -->
    <section class="stats-grid">
      <StatCard label="累计诊断" :value="userStore.stats?.total_diagnoses || 0" icon="microscope" accent="accent" />
      <StatCard label="病害记录" :value="userStore.categoryStats['fungal_disease'] || 0" icon="fungus" accent="accent" />
      <StatCard label="虫害记录" :value="userStore.categoryStats['pest'] || 0" icon="bug" accent="accent" />
      <StatCard label="缺肥/药害" :value="(userStore.categoryStats['deficiency'] || 0) + (userStore.categoryStats['phytotoxicity'] || 0)" icon="trendDown" accent="tech" />
    </section>

    <!-- 筛选栏 -->
    <div class="card filter-bar">
      <el-select v-model="filterCoarse" placeholder="按大类筛选" @change="load" style="width: 140px">
        <el-option v-for="o in coarseOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-input v-model="search" placeholder="搜索诊断名称（当前页）…" :prefix-icon="Search" clearable @change="load" style="width: 200px" />
      <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
        end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" />
      <el-select v-model="sortBy" style="width: 140px">
        <el-option v-for="o in sortOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <span class="total">当前页 {{ filteredItems.length }} / 共 {{ store.historyTotal }} 条</span>
      <el-button :icon="RefreshCw" @click="load" :loading="loading">刷新</el-button>
    </div>

    <!-- 列表 -->
    <div class="list">
      <EmptyState v-if="!filteredItems.length && !loading" icon="folder" title="暂无诊断记录"
        description="去识别页上传作物叶片，开始智能诊断吧" action-text="前往识别"
        @action="$router.push('/recognize')" />
      <div class="grid-list" v-else-if="loading && !filteredItems.length">
        <div v-for="i in 6" :key="i" class="hist-card card skeleton-hist">
          <Skeleton shape="rect" width="80px" height="80px" radius="var(--radius-md)" />
          <div class="hc-body">
            <Skeleton shape="text" width="60%" height="16px" />
            <Skeleton shape="text" width="40%" height="12px" />
            <Skeleton shape="text" width="50%" height="12px" />
          </div>
        </div>
      </div>
      <div class="grid-list" v-else>
        <div class="hist-card card" v-for="item in filteredItems" :key="item.id" @click="viewDetail(item.id)">
          <div class="hc-thumb"><img :src="item.image_url" @error="onThumbError" /></div>
          <div class="hc-body">
            <div class="hc-head">
              <h3>{{ item.fine_label || item.coarse_label }}</h3>
              <el-tag size="small" effect="plain">{{ item.coarse_label }}</el-tag>
            </div>
            <div class="hc-meta">
              <el-tag size="small" :type="SEV[item.severity]?.type" effect="dark">{{ SEV[item.severity]?.label }}</el-tag>
              <span class="conf">置信度 {{ (item.confidence * 100).toFixed(0) }}%</span>
            </div>
            <span class="hc-time">{{ new Date(item.created_at).toLocaleString('zh-CN') }}</span>
          </div>
          <div class="hc-actions" @click.stop>
            <el-button :icon="Eye" circle text @click="viewDetail(item.id)" />
            <el-button :icon="Trash2" circle type="danger" @click="remove(item.id)" />
          </div>
        </div>
      </div>
    </div>

    <el-pagination v-if="store.historyTotal > pageSize" layout="prev, pager, next" :total="store.historyTotal"
      :page-size="pageSize" v-model:current-page="page" @current-change="load" class="pager" />

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="诊断详情" size="560px">
      <div v-if="detail" class="detail">
        <DetectionCanvas v-if="detail.detection_boxes?.length"
          :image-url="detail.image_url" :boxes="detail.detection_boxes"
          :category="detail.coarse_category" :label="detail.fine_label || detail.coarse_label"
          class="detail-img" />
        <el-image v-else :src="detail.image_url" :preview-src-list="[detail.image_url]" fit="contain"
          class="detail-img" hide-on-click-modal :preview-teleported="true" />
        <div class="detail-head">
          <div class="detail-head-main">
            <h2>{{ detail.fine_label || detail.coarse_label }}</h2>
            <div class="detail-tags">
              <CategoryBadge :category="detail.coarse_category" size="sm" />
              <el-tag :type="SEV[detail.severity]?.type" effect="dark" size="small">{{ SEV[detail.severity]?.label }}</el-tag>
            </div>
          </div>
          <ConfidenceRing :value="detail.confidence" :accent="detail.confidence >= 0.8 ? 'accent' : detail.confidence >= 0.5 ? 'warning' : 'danger'" label="置信度" />
        </div>
        <div class="detail-scheme" v-if="detail.scheme">
          <el-alert :title="detail.scheme.diagnosis" :description="detail.scheme.cause" type="info" :closable="false" show-icon />
          <div v-if="detail.scheme.chemicals?.length" class="ds-block">
            <h4>推荐用药</h4>
            <p v-for="c in detail.scheme.chemicals" :key="c.name">· {{ c.name }}：{{ c.dose }}</p>
          </div>
          <div v-if="detail.scheme.green_alternatives?.length" class="ds-block">
            <h4>绿色方案</h4>
            <p v-for="g in detail.scheme.green_alternatives" :key="g.name">· {{ g.name }}：{{ g.dose }}</p>
          </div>
          <div v-if="detail.rag_advice" class="ds-block">
            <h4>AI 建议</h4>
            <div class="ds-rag">{{ detail.rag_advice }}</div>
          </div>
        </div>
      </div>
      <div v-else class="detail-skeleton">
        <Skeleton shape="rect" width="100%" height="220px" radius="var(--radius-lg)" />
        <div class="ds-sk-head">
          <Skeleton shape="text" width="60%" height="24px" />
          <Skeleton shape="text" width="80px" height="22px" />
        </div>
        <Skeleton shape="rect" width="100%" height="60px" radius="var(--radius-md)" />
        <div class="ds-sk-block">
          <Skeleton shape="text" width="40%" height="16px" />
          <Skeleton shape="text" width="100%" height="14px" />
          <Skeleton shape="text" width="90%" height="14px" />
        </div>
        <div class="ds-sk-block">
          <Skeleton shape="text" width="30%" height="16px" />
          <Skeleton shape="rect" width="100%" height="48px" radius="var(--radius-md)" />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.filter-bar { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.total { margin-left: auto; color: var(--fg-muted); font-size: var(--text-sm); }

.grid-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.hist-card { display: flex; gap: var(--space-2); padding: var(--space-3); cursor: pointer; transition: var(--transition); }
.skeleton-hist { cursor: default; }
.skeleton-hist .hc-body { display: flex; flex-direction: column; gap: var(--space-2); justify-content: center; }
.hist-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); border-color: var(--accent); }
.hc-thumb { width: 80px; height: 80px; border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; background: var(--bg-muted); }
.hc-thumb img { width: 100%; height: 100%; object-fit: cover; }
.hc-body { flex: 1; min-width: 0; }
.hc-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); margin-bottom: var(--space-2); }
.hc-head h3 { font-size: var(--text-base); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hc-meta { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.conf { font-size: var(--text-xs); color: var(--fg-muted); }
.hc-time { font-size: var(--text-xs); color: var(--fg-subtle); }
.hc-actions { display: flex; gap: 4px; align-self: flex-start; }

.pager { margin-top: 10px; justify-content: center; }

.detail-img { width: 100%; border-radius: var(--radius-lg); margin-bottom: var(--space-2); cursor: zoom-in; }
.detail-img :deep(img) { width: 100%; border-radius: var(--radius-lg); }
.thumb-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: var(--text-xs); color: var(--fg-subtle); }
.detail-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-2); }
.detail-head-main { flex: 1; min-width: 0; }
.detail-head h2 { margin-bottom: var(--space-2); }
.detail-tags { display: flex; gap: var(--space-2); }
.detail-scheme h4 { margin: var(--space-4) 0 var(--space-2); color: var(--accent); font-size: var(--text-sm); }
.ds-block p { font-size: var(--text-sm); color: var(--fg-secondary); margin-bottom: 4px; }
.ds-rag { background: var(--accent-soft); padding: var(--space-3); border-radius: var(--radius-md); white-space: pre-wrap; font-size: var(--text-sm); }

.detail-skeleton { display: flex; flex-direction: column; gap: 10px; }
.ds-sk-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.ds-sk-block { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }

@media (max-width: 1024px) { .stats-grid, .grid-list { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .stats-grid, .grid-list { grid-template-columns: 1fr; } }
</style>