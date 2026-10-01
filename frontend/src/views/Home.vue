<script setup>
import { ref, computed, onMounted, onBeforeUnmount, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import StatCard from '@/components/StatCard.vue'
import CategoryBadge from '@/components/CategoryBadge.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import Chart from '@/components/Chart.vue'
import Skeleton from '@/components/Skeleton.vue'
import AppIcon from '@/components/AppIcon.vue'
import { Camera, MessagesSquare, FileText, Calendar, ArrowRight, Cpu, Wifi, ShieldCheck, Database } from 'lucide-vue-next'

const router = useRouter()
const userStore = useUserStore()
const loading = computed(() => userStore.loading)

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
function hexToRgba(hex, alpha) {
  const h = (hex || '#1FB96B').replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}
const isDark = ref(document.documentElement.getAttribute('data-theme') === 'dark')
const chartColors = computed(() => {
  const bg = isDark.value ? '#0E1B14' : '#ffffff'
  const border = cssVar('--border') || '#1e3326'
  const fg = cssVar('--fg') || '#e8f2ea'
  const fgMuted = cssVar('--fg-muted') || '#8fa399'
  const splitLine = isDark.value ? '#1e3326' : '#ede8db'
  const accent = cssVar('--accent') || '#1fb96b'
  const fungal = cssVar('--cat-fungal') || '#fb923c'
  const pest = cssVar('--cat-pest') || '#f87171'
  const deficiency = cssVar('--cat-deficiency') || '#fbbf24'
  const phytotoxicity = cssVar('--cat-phytotoxicity') || '#c084fc'
  return { bg, border, fg, fgMuted, splitLine, accent, fungal, pest, deficiency, phytotoxicity }
})

let themeObserver
onMounted(() => {
  userStore.loadSystemInfo(); userStore.loadStats()
  themeObserver = new MutationObserver(() => {
    isDark.value = document.documentElement.getAttribute('data-theme') === 'dark'
  })
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})
onBeforeUnmount(() => themeObserver?.disconnect())
/* KeepAlive 缓存后，重新进入首页时刷新统计（首次挂载由 onMounted 负责，避免重复请求） */
let actCount = 0
onActivated(() => { actCount += 1; if (actCount > 1) { userStore.loadSystemInfo(); userStore.loadStats() } })

const stats = computed(() => userStore.stats || { total_diagnoses: 0, by_category: {}, categories_supported: 4, fine_classes_supported: 23 })
const catData = computed(() => {
  const c = stats.value.by_category || {}
  const cc = chartColors.value
  // FUNC-006：key 用英文大类，展示名从后端返回的 label 映射取（缺省回退固定中文）
  const labels = stats.value.by_category_labels || {}
  const zh = (k, fallback) => labels[k] || fallback
  return [
    { name: zh('fungal_disease', '真菌病害'), value: c['fungal_disease'] || 0, color: cc.fungal },
    { name: zh('pest', '虫害'), value: c['pest'] || 0, color: cc.pest },
    { name: zh('deficiency', '土壤缺肥'), value: c['deficiency'] || 0, color: cc.deficiency },
    { name: zh('phytotoxicity', '农药药害'), value: c['phytotoxicity'] || 0, color: cc.phytotoxicity },
  ]
})

const trendOption = computed(() => {
  const c = chartColors.value
  const total = stats.value.total_diagnoses || 0
  const data = [Math.max(1, total - 5), Math.max(1, total - 4), Math.max(1, total - 3), Math.max(1, total - 2), Math.max(1, total - 1), total || 1, Math.max(1, total + 1)]
  return {
    tooltip: { trigger: 'axis', backgroundColor: c.bg, borderColor: c.border, textStyle: { color: c.fg } },
    grid: { left: 36, right: 16, top: 20, bottom: 28 },
    xAxis: {
      type: 'category', boundaryGap: false,
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '今日'],
      axisLine: { lineStyle: { color: c.border } }, axisLabel: { color: c.fgMuted },
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: c.splitLine } }, axisLabel: { color: c.fgMuted } },
    series: [{
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 7, showSymbol: false,
      data,
      lineStyle: { width: 3, color: c.accent }, itemStyle: { color: c.accent },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
        { offset: 0, color: hexToRgba(c.accent, 0.28) }, { offset: 1, color: hexToRgba(c.accent, 0) }] } },
    }],
  }
})

const pieOption = computed(() => {
  const c = chartColors.value
  return {
    tooltip: { trigger: 'item', backgroundColor: c.bg, borderColor: c.border, textStyle: { color: c.fg } },
    legend: { bottom: 0, icon: 'circle', textStyle: { color: c.fgMuted, fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['54%', '74%'], center: ['50%', '42%'], avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: c.bg, borderWidth: 3 },
      label: { show: false }, emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', color: c.fg } },
      data: catData.value.map(d => ({ name: d.name, value: d.value || 1, itemStyle: { color: d.color } })),
    }],
  }
})

const categories = [
  { key: 'fungal_disease', label: '真菌病害', desc: '稻瘟病、锈病、白粉病等真菌感染', count: '9 类', icon: 'fungus' },
  { key: 'pest', label: '虫害', desc: '蚜虫、飞虱、螟虫等昆虫危害', count: '6 类', icon: 'bug' },
  { key: 'deficiency', label: '土壤缺肥', desc: '缺氮黄化、缺钾焦枯等营养缺乏', count: '4 类', icon: 'trendDown' },
  { key: 'phytotoxicity', label: '农药药害', desc: '药液斑驳、灼伤等施药不当', count: '1 类', icon: 'warning' },
]
const innovations = [
  { icon: 'brain', title: '多模态四分类', desc: '精准区分病害/虫害/缺肥/药害，解决肉眼混淆痛点' },
  { icon: 'sprout', title: '小样本泛化', desc: '田间数据增强 + 迁移学习，少量样本高泛化' },
  { icon: 'broadcast', title: '离线轻量化', desc: 'INT8 量化 + CPU 推理，农村弱网可用' },
  { icon: 'sparkles', title: 'AI 农事顾问', desc: '农业垂直 RAG 知识库，输出绿色农事方案' },
]
const quickActions = [
  { icon: Camera, label: '拍照识别', desc: '上传叶片智能诊断', path: '/recognize', accent: 'accent' },
  { icon: MessagesSquare, label: 'AI 顾问', desc: '农事问答与方案', path: '/advisor', accent: 'tech' },
  { icon: Calendar, label: '农事日历', desc: '节气种植建议', path: '/calendar', accent: 'lime' },
  { icon: FileText, label: '诊断档案', desc: '历史记录追溯', path: '/history', accent: 'accent' },
]

const systemStatus = [
  { icon: Cpu, label: '诊断模型', value: '多模态 v2 在线', tone: 'accent' },
  { icon: Wifi, label: '网络依赖', value: '离线可用', tone: 'lime' },
  { icon: ShieldCheck, label: '数据隐私', value: '本地存储', tone: 'accent' },
  { icon: Database, label: '知识库', value: '农业 RAG 已加载', tone: 'tech' },
]
const sparks = {
  total: [3, 5, 4, 7, 6, 9, 11],
  cat: [2, 3, 3, 4, 5, 6, 7],
  fine: [1, 2, 2, 3, 4, 5, 6],
  offline: [6, 6, 6, 6, 6, 6, 6],
}
</script>

<template>
  <div class="page">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <div class="hero-tag"><span class="dot"></span> 多模态小样本 · 国赛参赛系统</div>
        <h1 class="hero-title">农作物病虫害<br /><span class="text-gradient-accent">智能诊断</span>与<span class="text-gradient-lime">农事顾问</span></h1>
        <p class="hero-desc">手机拍照离线识别病虫害 · 自动溯源减产原因 · 智能生成绿色农事方案 · 打造轻量化普惠式 AI 农技助手</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="router.push('/recognize')">
            <el-icon><Camera /></el-icon>&nbsp;立即识别
          </el-button>
          <el-button size="large" @click="router.push('/advisor')">
            <el-icon><MessagesSquare /></el-icon>&nbsp;AI 顾问
          </el-button>
        </div>
        <div class="hero-stats-inline">
          <div><strong>23</strong><span>细分类别</span></div>
          <div><strong>4</strong><span>问题大类</span></div>
          <div><strong>100%</strong><span>离线可用</span></div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="orb">
          <div class="ring ring-1"></div>
          <div class="ring ring-2"></div>
          <div class="ring ring-3"></div>
          <div class="orb-core"><AppIcon name="leaf" :size="52" /></div>
        </div>
        <div class="float-chip chip-a"><AppIcon name="fungus" :size="14" /> 真菌病害</div>
        <div class="float-chip chip-b"><AppIcon name="bug" :size="14" /> 虫害</div>
        <div class="float-chip chip-c"><AppIcon name="trendDown" :size="14" /> 缺肥</div>
        <div class="float-chip chip-d"><AppIcon name="sparkles" :size="14" /> AI 方案</div>
      </div>
    </section>

    <!-- 统计磁贴 -->
    <section class="stats-grid">
      <template v-if="loading">
        <div v-for="i in 4" :key="i" class="card skeleton-card">
          <Skeleton shape="text" width="60%" height="13px" />
          <Skeleton shape="text" width="40%" height="28px" />
        </div>
      </template>
      <template v-else>
        <StatCard label="累计诊断" :value="stats.total_diagnoses" icon="microscope" accent="accent" :trend="12" :spark="sparks.total" />
        <StatCard label="支持大类" :value="stats.categories_supported" icon="target" accent="tech" :spark="sparks.cat" />
        <StatCard label="细分类别" :value="stats.fine_classes_supported" icon="clipboard" accent="accent" :spark="sparks.fine" />
        <StatCard label="离线可用" value="100%" icon="broadcast" accent="lime" :spark="sparks.offline" />
      </template>
    </section>

    <!-- 数据可视化 -->
    <section class="charts-grid" v-reveal>
      <div class="card chart-card">
        <SectionHeader title="诊断趋势" subtitle="近 7 日诊断量变化" icon="trendUp" index="01" />
        <Skeleton v-if="loading" shape="rect" width="100%" height="260px" radius="var(--radius-md)" />
        <Chart v-else :option="trendOption" height="260px" />
      </div>
      <div class="card chart-card">
        <SectionHeader title="问题分布" subtitle="四大类占比" icon="pieChart" index="02" />
        <Skeleton v-if="loading" shape="rect" width="100%" height="260px" radius="var(--radius-md)" />
        <Chart v-else :option="pieOption" height="260px" />
      </div>
    </section>

    <!-- 快速操作 -->
    <section v-reveal data-delay="1">
      <SectionHeader title="快速操作" subtitle="一键进入核心功能" icon="sparkles" index="03" />
      <div class="quick-grid">
        <div v-for="a in quickActions" :key="a.path" class="quick-card" :style="{ '--c': `var(--${a.accent})`, '--cs': `var(--${a.accent}-soft)` }" @click="router.push(a.path)">
          <div class="quick-icon"><el-icon><component :is="a.icon" /></el-icon></div>
          <div class="quick-text">
            <strong>{{ a.label }}</strong>
            <span>{{ a.desc }}</span>
          </div>
          <el-icon class="quick-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </section>

    <!-- 四分类能力 -->
    <section v-reveal data-delay="2">
      <SectionHeader title="多模态四分类识别" subtitle="精准区分田间四类易混淆问题" icon="target" index="04" />
      <div class="cat-grid">
        <div v-for="c in categories" :key="c.key" class="cat-card">
          <div class="cat-head">
            <CategoryBadge :category="c.key" size="lg" />
            <span class="cat-count">{{ c.count }}</span>
          </div>
          <div class="cat-icon"><AppIcon :name="c.icon" :size="30" /></div>
          <p class="cat-desc">{{ c.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 创新点 -->
    <section class="card innov-card" v-reveal data-delay="3">
      <SectionHeader title="核心创新点" subtitle="国赛得分关键 · 区别市面普通病害识别" icon="sparkles" index="05" />
      <div class="innov-grid">
        <div v-for="i in innovations" :key="i.title" class="innov-item">
          <div class="innov-icon"><AppIcon :name="i.icon" :size="22" /></div>
          <div>
            <strong>{{ i.title }}</strong>
            <p>{{ i.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 系统状态条 -->
    <section class="status-strip" v-reveal data-delay="4">
      <div class="ss-item" v-for="s in systemStatus" :key="s.label">
        <span class="ss-icon" :class="s.tone"><el-icon><component :is="s.icon" /></el-icon></span>
        <div class="ss-text">
          <strong>{{ s.value }}</strong>
          <span>{{ s.label }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-6); position: relative; overflow: hidden;
  box-shadow: var(--shadow-md);
}
.hero::before {
  content: ''; position: absolute; top: -140px; right: -120px;
  width: 460px; height: 460px; border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--accent) 20%, transparent), transparent 65%);
  pointer-events: none;
}
.hero::after {
  content: ''; position: absolute; bottom: -160px; left: -80px;
  width: 380px; height: 380px; border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--lime) 12%, transparent), transparent 65%);
  pointer-events: none;
}
.hero-content { position: relative; z-index: 1; max-width: 600px; }
.hero-tag {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--accent-soft); color: var(--accent-hover);
  padding: var(--space-2) 14px; border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: 600; margin-bottom: var(--space-4);
}
.hero-tag .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--success); animation: pulse-soft 2s infinite; }
.hero-title { font-size: var(--text-4xl); font-weight: var(--weight-extrabold); letter-spacing: -0.035em; line-height: 1.1; margin-bottom: var(--space-4); }
.hero-desc { color: var(--fg-muted); font-size: var(--text-md); line-height: var(--leading-relaxed); margin-bottom: var(--space-5); max-width: 520px; }
.hero-actions { display: flex; gap: var(--space-3); }
.hero-stats-inline { display: flex; gap: var(--space-6); margin-top: var(--space-5); }
.hero-stats-inline div { display: flex; flex-direction: column; }
.hero-stats-inline strong { font-family: var(--font-display); font-size: var(--text-2xl); font-weight: var(--weight-extrabold); color: var(--fg); }
.hero-stats-inline span { font-size: var(--text-xs); color: var(--fg-subtle); margin-top: 2px; }

.hero-visual { position: relative; width: 280px; height: 280px; flex-shrink: 0; }
.orb { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
.ring { position: absolute; border-radius: 50%; border: 2px solid; }
.ring-1 { inset: 0; border-color: color-mix(in srgb, var(--accent) 30%, transparent); animation: spin 50s linear infinite; }
.ring-2 { inset: 34px; border-color: color-mix(in srgb, var(--tech) 36%, transparent); border-style: dashed; animation: spin 36s linear infinite reverse; }
.ring-3 { inset: 68px; border-color: color-mix(in srgb, var(--lime) 40%, transparent); animation: spin 28s linear infinite; }
.orb-core {
  width: 110px; height: 110px; border-radius: 50%;
  background: var(--accent-gradient); color: var(--fg-on-accent);
  display: flex; align-items: center; justify-content: center;
  box-shadow: var(--shadow-accent-lg); animation: float 5s ease-in-out infinite;
}
.float-chip {
  position: absolute; display: inline-flex; align-items: center; gap: 6px;
  background: var(--glass-bg); border: 1px solid var(--glass-border);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-full);
  font-size: var(--text-xs); font-weight: 600; color: var(--fg);
  box-shadow: var(--shadow-sm); z-index: 2;
}
.chip-a { top: 8px; left: -10px; animation: float 6s ease-in-out infinite; }
.chip-b { top: 36px; right: -16px; animation: float 5.4s ease-in-out infinite 0.4s; }
.chip-c { bottom: 40px; left: -8px; animation: float 5.8s ease-in-out infinite 0.2s; }
.chip-d { bottom: 10px; right: -6px; color: var(--lime); animation: float 6.4s ease-in-out infinite 0.6s; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); }
.skeleton-card { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-4); }

.charts-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: var(--space-4); }
.chart-card { padding: var(--space-4); }

.quick-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); }
.quick-card {
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: var(--space-4); display: flex; align-items: center; gap: var(--space-3);
  cursor: pointer; transition: transform var(--duration) var(--ease-out), box-shadow var(--duration) var(--ease-out), border-color var(--duration);
}
.quick-card:hover { box-shadow: var(--shadow-md); transform: translateY(-3px); border-color: color-mix(in srgb, var(--c) 45%, var(--border)); }
.quick-icon { width: 46px; height: 46px; border-radius: var(--radius-md); color: var(--c); background: var(--cs); display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; transition: var(--transition); }
.quick-card:hover .quick-icon { transform: scale(1.06); }
.quick-text { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.quick-text strong { font-size: var(--text-md); color: var(--fg); }
.quick-text span { font-size: var(--text-sm); color: var(--fg-muted); }
.quick-arrow { color: var(--fg-subtle); transition: var(--transition); }
.quick-card:hover .quick-arrow { color: var(--c); transform: translateX(4px); }

.cat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4); }
.cat-card {
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: var(--space-4); transition: transform var(--duration) var(--ease-out), box-shadow var(--duration) var(--ease-out);
}
.cat-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-4px); }
.cat-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3); }
.cat-count { font-family: var(--font-mono); font-size: var(--text-xs); color: var(--fg-subtle); }
.cat-icon { margin-bottom: var(--space-3); color: var(--accent); display: flex; align-items: center; }
.cat-desc { font-size: var(--text-sm); color: var(--fg-muted); line-height: var(--leading-relaxed); }

.innov-card { padding: var(--space-4) var(--space-5); }
.innov-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-5); }
.innov-item { display: flex; gap: var(--space-3); }
.innov-icon { width: 44px; height: 44px; border-radius: var(--radius-md); background: var(--accent-soft); color: var(--accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.innov-item strong { font-size: var(--text-md); display: block; margin-bottom: 4px; color: var(--fg); }
.innov-item p { font-size: var(--text-sm); color: var(--fg-muted); line-height: var(--leading-relaxed); }

.status-strip {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-4);
  background: var(--bg-elevated); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: var(--space-4) var(--space-5);
}
.ss-item { display: flex; align-items: center; gap: var(--space-3); }
.ss-icon { width: 40px; height: 40px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: var(--bg-muted); color: var(--fg-muted); }
.ss-icon.accent { background: var(--accent-soft); color: var(--accent); }
.ss-icon.lime { background: var(--lime-soft); color: var(--lime); }
.ss-icon.tech { background: var(--tech-soft); color: var(--tech); }
.ss-text { display: flex; flex-direction: column; line-height: 1.3; min-width: 0; }
.ss-text strong { font-size: var(--text-sm); color: var(--fg); font-weight: 600; }
.ss-text span { font-size: var(--text-xs); color: var(--fg-subtle); }

@media (max-width: 1100px) {
  .stats-grid, .quick-grid, .cat-grid, .status-strip { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .innov-grid { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .hero { flex-direction: column; text-align: center; padding: var(--space-6); }
  .hero-content { max-width: none; }
  .hero-actions, .hero-stats-inline { justify-content: center; }
  .hero-visual { display: none; }
}
@media (max-width: 560px) {
  .stats-grid, .quick-grid, .cat-grid, .status-strip { grid-template-columns: 1fr; }
}
</style>
