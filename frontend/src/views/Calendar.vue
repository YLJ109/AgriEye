<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/api'
import SectionHeader from '@/components/SectionHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import Skeleton from '@/components/Skeleton.vue'
import { Plus, Trash2 } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'

const terms = ref([])
const currentAdvice = ref(null)
const reminders = ref([])
const loading = ref(true)
const newReminder = ref({ title: '', content: '', crop: '', priority: 1 })
const selectedCrop = ref('')
const crops = ['水稻', '小麦', '玉米', '番茄', '黄瓜', '苹果', '柑橘']
const PRIO = { 1: { label: '低', type: 'info' }, 2: { label: '中', type: 'warning' }, 3: { label: '高', type: 'danger' } }

// 节气详情抽屉
const termDetailVisible = ref(false)
const selectedTerm = ref(null)
function showTermDetail(t) {
  selectedTerm.value = t
  termDetailVisible.value = true
}

const currentTermIdx = computed(() => terms.value.findIndex(t => t.term === currentAdvice.value?.solar_term))

async function loadTerms() { try { terms.value = (await api.solarTerms()).terms } catch { /* ignore */ } }
async function loadAdvice() { try { currentAdvice.value = await api.currentAdvice(selectedCrop.value) } catch { /* ignore */ } }
async function loadReminders() { try { reminders.value = await api.listReminders() } catch { /* ignore */ } }
async function addReminder() {
  if (!newReminder.value.title) { ElMessage.warning('请填写标题'); return }
  try {
    await api.createReminder({ ...newReminder.value, solar_term: currentAdvice.value?.solar_term })
    newReminder.value = { title: '', content: '', crop: '', priority: 1 }
    ElMessage.success('提醒已添加'); loadReminders()
  } catch { /* api 拦截器已提示 */ }
}
async function toggle(r) {
  const old = r.done
  r.done = !r.done
  try { await api.toggleReminder(r.id) } catch { r.done = old; ElMessage.error('操作失败') }
}
async function remove(r) {
  try {
    await ElMessageBox.confirm(`确定删除提醒「${r.title}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
    await api.deleteReminder(r.id)
    ElMessage.success('已删除')
    loadReminders()
  } catch { /* 用户取消 */ }
}
onMounted(async () => {
  loading.value = true
  try { await Promise.all([loadTerms(), loadAdvice(), loadReminders()]) } finally { loading.value = false }
})
</script>

<template>
  <div class="page">

    <!-- 当前节气大卡 -->
    <section class="card current-card" v-if="currentAdvice && !loading" v-reveal>
      <div class="card-glow"></div>
      <div class="current-left">
        <div class="current-date">{{ currentAdvice.date?.slice(5) }}</div>
        <div class="current-term">
          <h2>{{ currentAdvice.solar_term }}</h2>
          <span class="current-year">{{ currentAdvice.date?.slice(0, 4) }} 年</span>
        </div>
      </div>
      <div class="current-right">
        <div class="advice-label"><AppIcon name="clipboard" :size="16" /> 农事建议</div>
        <p class="advice-text">{{ currentAdvice.advice }}</p>
        <p class="crop-tip" v-if="currentAdvice.crop_tip">{{ currentAdvice.crop_tip }}</p>
        <div class="crop-select">
          <el-select v-model="selectedCrop" aria-label="选择作物" placeholder="选择作物查看针对性建议" clearable @change="loadAdvice" size="small">
            <el-option v-for="c in crops" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
      </div>
    </section>
    <section class="card skeleton-current" v-if="loading">
      <Skeleton shape="rect" width="100%" height="120px" radius="var(--radius-lg)" />
    </section>

    <!-- 二十四节气时间轴 -->
    <section class="card" v-reveal data-delay="1">
      <SectionHeader title="二十四节气农事要点" subtitle="点击查看各节气农事" icon="leaf" />
      <div class="term-timeline" v-if="!loading">
        <div class="term-node" v-for="(t, i) in terms" :key="t.term"
          :class="{ active: i === currentTermIdx, passed: i < currentTermIdx }"
          @click="showTermDetail(t)">
          <div class="term-dot"></div>
          <div class="term-card">
            <strong>{{ t.term }}</strong>
            <p>{{ t.advice }}</p>
          </div>
        </div>
      </div>
      <div class="term-timeline" v-else>
        <div v-for="i in 6" :key="i" class="term-node">
          <Skeleton shape="circle" width="12px" height="12px" />
          <Skeleton shape="rect" width="100%" height="60px" radius="var(--radius-md)" />
        </div>
      </div>
    </section>

    <div class="two-col">
      <!-- 添加提醒 -->
      <section class="card" v-reveal data-delay="2">
        <SectionHeader title="添加农事提醒" icon="plus" />
        <div class="form">
          <el-input v-model="newReminder.title" aria-label="提醒标题" placeholder="提醒标题" maxlength="60" show-word-limit />
          <div class="form-row">
            <el-select v-model="newReminder.crop" aria-label="作物" placeholder="作物" clearable>
              <el-option v-for="c in crops" :key="c" :label="c" :value="c" />
            </el-select>
            <el-select v-model="newReminder.priority" aria-label="优先级" placeholder="优先级">
              <el-option label="低" :value="1" /><el-option label="中" :value="2" /><el-option label="高" :value="3" />
            </el-select>
          </div>
          <el-input v-model="newReminder.content" type="textarea" placeholder="提醒内容" :rows="3" maxlength="200" show-word-limit />
          <el-button type="primary" @click="addReminder"><el-icon><Plus /></el-icon>&nbsp;添加提醒</el-button>
        </div>
      </section>

      <!-- 提醒列表 -->
      <section class="card" v-reveal data-delay="3">
        <SectionHeader title="我的农事提醒" :subtitle="`${reminders.length} 条`" icon="clock" />
        <EmptyState v-if="!reminders.length && !loading" icon="bell" title="暂无提醒" description="添加农事提醒，科学安排农事" />
        <div class="reminder-list" v-else-if="loading">
          <div v-for="i in 3" :key="i" class="reminder-item skeleton-reminder">
            <Skeleton shape="circle" width="18px" height="18px" />
            <div class="r-content" style="display:flex;flex-direction:column;gap:var(--space-2)">
              <Skeleton shape="text" width="50%" height="14px" />
              <Skeleton shape="text" width="80%" height="12px" />
            </div>
          </div>
        </div>
        <div class="reminder-list" v-else>
          <div class="reminder-item" v-for="r in reminders" :key="r.id" :class="{ done: r.done }">
            <el-checkbox :model-value="r.done" @change="toggle(r)" />
            <div class="r-content">
              <div class="r-head">
                <strong>{{ r.title }}</strong>
                <el-tag size="small" :type="PRIO[r.priority]?.type" effect="plain">{{ PRIO[r.priority]?.label }}</el-tag>
              </div>
              <div class="r-meta">
                <el-tag v-if="r.crop" size="small" effect="plain">{{ r.crop }}</el-tag>
                <el-tag v-if="r.solar_term" size="small" effect="plain">{{ r.solar_term }}</el-tag>
              </div>
              <p v-if="r.content">{{ r.content }}</p>
            </div>
            <el-button :icon="Trash2" circle text type="danger" @click="remove(r)" />
          </div>
        </div>
      </section>
    </div>

    <!-- 节气详情抽屉 -->
    <el-drawer v-model="termDetailVisible" title="节气农事详情" size="440px">
      <div v-if="selectedTerm" class="term-detail">
        <div class="td-head">
          <div class="td-icon"><AppIcon name="leaf" :size="24" /></div>
          <div>
            <h2>{{ selectedTerm.term }}</h2>
            <p class="td-date" v-if="selectedTerm.date">{{ selectedTerm.date }}</p>
          </div>
        </div>
        <div class="td-section">
          <div class="td-label"><AppIcon name="clipboard" :size="16" /> 农事建议</div>
          <p class="td-text">{{ selectedTerm.advice }}</p>
        </div>
        <div class="td-section" v-if="selectedTerm.crop_tip">
          <div class="td-label"><AppIcon name="eco" :size="16" /> 作物提示</div>
          <p class="td-text">{{ selectedTerm.crop_tip }}</p>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.current-card { display: flex; gap: var(--space-5); padding: var(--space-5); background: var(--fusion-gradient); color: #fff; border: none; position: relative; overflow: hidden; box-shadow: var(--shadow-accent); }
.skeleton-current { padding: var(--space-3); }
.card-glow { position: absolute; top: -70px; right: -40px; width: 260px; height: 260px; border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,0.28), transparent 70%); pointer-events: none; }
.current-card::before { content: ''; position: absolute; bottom: -90px; left: -30px; width: 220px; height: 220px; border-radius: 50%; background: rgba(255,255,255,0.12); pointer-events: none; }
.current-left { display: flex; flex-direction: column; gap: var(--space-2); flex-shrink: 0; position: relative; z-index: 1; }
.current-date { font-family: var(--font-mono); font-size: var(--text-2xl); opacity: 0.95; color: #fff; }
.current-term h2 { color: #fff; font-size: var(--text-3xl); }
.current-year { font-size: var(--text-sm); opacity: 0.85; color: #fff; }
.current-right { flex: 1; position: relative; z-index: 1; }
.advice-label { font-size: var(--text-sm); opacity: 0.92; margin-bottom: var(--space-2); display: flex; align-items: center; gap: var(--space-2); color: #fff; }
.advice-text { font-size: var(--text-md); line-height: var(--leading-relaxed); margin-bottom: var(--space-2); color: #fff; }
.crop-tip { background: rgba(255,255,255,0.18); padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); font-size: var(--text-sm); color: #fff; }
.crop-select { margin-top: var(--space-3); }
.crop-select :deep(.el-select) { width: 220px; }
.crop-select :deep(.el-select .el-select__wrapper) { background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3); box-shadow: none; }
.crop-select :deep(.el-select .el-select__placeholder) { color: rgba(255,255,255,0.85); }
/* 亮色主题：wrapper 被 global 的 --bg-elevated !important 覆盖为白底，文字必须转黑，否则白字白底不可见 */
[data-theme="light"] .crop-select :deep(.el-select .el-select__placeholder),
[data-theme="light"] .crop-select :deep(.el-select .el-select__selected-item) { color: var(--fg); }
[data-theme="light"] .crop-select :deep(.el-select .el-select__caret) { color: var(--fg-secondary); }

.term-timeline { display: grid; grid-template-columns: repeat(6, 1fr); gap: var(--space-2); }
.term-node { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.term-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--border-strong); transition: var(--transition); }
.term-node.active .term-dot { background: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.term-node.passed .term-dot { background: var(--accent-secondary); opacity: 0.5; }
.term-card { background: var(--bg-muted); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-3); text-align: center; transition: var(--transition); }
.term-node.active .term-card { background: var(--accent-soft); border-color: var(--accent); }
/* UX-002：--accent-hover 在 --accent-soft 底上只有 4.49:1（深）/4.09:1（浅），改用 --accent-text */
.term-card strong { display: block; color: var(--accent-text); font-size: var(--text-sm); margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.term-card p { font-size: var(--text-xs); color: var(--fg-muted); line-height: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.term-node { cursor: pointer; }
.term-node:hover .term-card { border-color: var(--accent); box-shadow: var(--shadow-sm); transform: translateY(-2px); }

/* 节气详情抽屉 */
.term-detail { display: flex; flex-direction: column; gap: var(--space-3); }
.td-head { display: flex; align-items: center; gap: var(--space-3); padding-bottom: var(--space-3); border-bottom: 1px solid var(--border); }
.td-icon { width: 48px; height: 48px; border-radius: var(--radius-md); background: var(--accent-soft); color: var(--accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.td-head h2 { font-size: var(--text-xl); color: var(--fg); }
.td-date { font-size: var(--text-sm); color: var(--fg-muted); margin-top: 4px; }
.td-section { background: var(--bg-muted); border-radius: var(--radius-md); padding: var(--space-3); }
.td-label { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); font-weight: 600; color: var(--accent); margin-bottom: var(--space-2); }
.td-text { font-size: var(--text-sm); color: var(--fg-secondary); line-height: 1.7; white-space: pre-wrap; }

.two-col { display: grid; grid-template-columns: 1fr 1.4fr; gap: 10px; }
.form { display: flex; flex-direction: column; gap: var(--space-2); }
.form-row { display: flex; gap: var(--space-2); }
.form-row > * { flex: 1; }

.reminder-list { display: flex; flex-direction: column; gap: var(--space-2); }
.reminder-item { display: flex; gap: var(--space-2); align-items: flex-start; padding: var(--space-3); border-radius: var(--radius-md); background: var(--bg-muted); transition: var(--transition); }
.skeleton-reminder { cursor: default; }
.reminder-item:hover { background: var(--bg-hover); }
.reminder-item.done { opacity: 0.6; }
.reminder-item.done strong { text-decoration: line-through; }
.r-content { flex: 1; }
.r-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: 4px; }
.r-meta { display: flex; gap: 4px; margin-bottom: 4px; }
.r-content p { font-size: var(--text-sm); color: var(--fg-muted); }

@media (max-width: 1024px) { .two-col { grid-template-columns: 1fr; } .term-timeline { grid-template-columns: repeat(4, 1fr); } .current-card { flex-direction: column; } }
@media (max-width: 640px) { .term-timeline { grid-template-columns: repeat(2, 1fr); } }
</style>