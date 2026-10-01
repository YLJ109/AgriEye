<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import DetectionCanvas from '@/components/DetectionCanvas.vue'
import ConfidenceRing from '@/components/ConfidenceRing.vue'
import MarkdownView from '@/components/MarkdownView.vue'
import { ElMessage } from 'element-plus'
import { ScanSearch, X, Check, Loader2, ImagePlus, Trash2, FileCheck2, AlertCircle, Sparkles, FileDown, CheckCheck, XCircle, Upload, ShieldCheck, Cpu, Database } from 'lucide-vue-next'

const router = useRouter()
const fileInput = ref(null)
const images = ref([])
const detecting = ref(false)
const submitting = ref(false)
const detectProgress = ref(0)
const SEV = { mild: '轻度', moderate: '中度', severe: '重度', none: '—' }

const MODE_MAP = {
  model: { text: 'AI 模型识别', cls: 'model' },
  heuristic: { text: '本地视觉分析', cls: 'heuristic' },
  unknown: { text: '未识别', cls: 'unknown' },
}
const modeText = (m) => MODE_MAP[m]?.text || 'AI 模型识别'
const modeClass = (m) => MODE_MAP[m]?.cls || 'model'

const mainTab = ref('review')
const selectedId = ref('')
const detailTab = ref('result')

const selected = computed(() => images.value.find(i => i.id === selectedId.value))
const doneList = computed(() => images.value.filter(i => i.result))
const selectedList = computed(() => doneList.value.filter(i => i.selected))
const allChecked = computed(() => { const d = doneList.value; return d.length > 0 && d.every(i => i.selected) })
const indeterminate = computed(() => { const d = doneList.value; const s = d.filter(i => i.selected).length; return s > 0 && s < d.length })

const aiScheme = ref('')
const schemeLoading = ref(false)
const schemeGenerated = ref(false)

/* 审核状态流水线：已传 → 检测中 → 完成 → 通过 → 入库 */
const STAGES = ['已传', '检测中', '完成', '通过', '入库']
const stageState = computed(() => {
  const s = selected.value?.status
  if (s === 'rejected') return { stage: 3, rejected: true, error: false }
  if (s === 'error') return { stage: 1, rejected: false, error: true }
  const map = { pending: 0, detecting: 1, done: 2, approved: 3, stored: 4 }
  return { stage: map[s] ?? -1, rejected: false, error: false }
})

const approvedCount = computed(() => images.value.filter(i => i.status === 'approved').length)
const storedCount = computed(() => images.value.filter(i => i.status === 'stored').length)
const hasPending = computed(() => images.value.some(i => i.status === 'pending' || i.status === 'error'))

function triggerUpload() { fileInput.value?.click() }

function onFilesChange(e) {
  const files = Array.from(e.target.files || [])
  for (const file of files) {
    if (!file.type.startsWith('image/')) continue
    if (file.size > 10 * 1024 * 1024) { ElMessage.warning(`${file.name} 超过10MB，已跳过`); continue }
    images.value.push({ id: Date.now() + Math.random(), file, url: URL.createObjectURL(file), status: 'pending', result: null, selected: false })
  }
  e.target.value = ''
}

function onDrop(e) {
  e.preventDefault()
  const files = Array.from(e.dataTransfer.files || [])
  for (const file of files) {
    if (!file.type.startsWith('image/')) continue
    images.value.push({ id: Date.now() + Math.random(), file, url: URL.createObjectURL(file), status: 'pending', result: null, selected: false })
  }
}

function removeImage(id) {
  const img = images.value.find(i => i.id === id)
  if (img) URL.revokeObjectURL(img.url)
  images.value = images.value.filter(i => i.id !== id)
  if (selectedId.value === id) { selectedId.value = ''; mainTab.value = 'review' }
}

async function detectAll() {
  const pending = images.value.filter(i => i.status === 'pending' || i.status === 'error')
  if (!pending.length) return
  detecting.value = true
  detectProgress.value = 0
  const total = pending.length
  let done = 0
  for (const img of pending) {
    img.status = 'detecting'
    try {
      const fd = new FormData()
      fd.append('file', img.file)
      fd.append('user_id', '1')
      fd.append('preview', 'true')
      const res = await api.recognize(fd)
      img.result = res
      img.status = 'done'
    } catch (e) {
      img.status = 'error'
      img.error = '检测失败，请重试'
    }
    done++
    detectProgress.value = Math.round((done / total) * 100)
  }
  detecting.value = false
  const ok = images.value.filter(i => i.status === 'done').length
  if (ok) ElMessage.success(`批量检测完成，${ok} 张成功`)
}

function approve(img) { img.status = 'approved' }
function reject(img) { img.status = 'rejected' }

function toggleSelectAll(val) { doneList.value.forEach(i => { i.selected = val }) }

function batchApprove() {
  const s = selectedList.value.filter(i => i.status !== 'approved')
  if (!s.length) { ElMessage.warning('请先勾选需要通过的记录'); return }
  s.forEach(i => { i.status = 'approved' })
  ElMessage.success(`已通过 ${s.length} 条记录`)
}

function batchReject() {
  const s = selectedList.value.filter(i => i.status !== 'rejected')
  if (!s.length) { ElMessage.warning('请先勾选需要拒绝的记录'); return }
  s.forEach(i => { i.status = 'rejected' })
  ElMessage.success(`已拒绝 ${s.length} 条记录`)
}

function batchDelete() {
  const s = selectedList.value
  if (!s.length) { ElMessage.warning('请先勾选需要删除的记录'); return }
  s.forEach(i => removeImage(i.id))
  ElMessage.success(`已删除 ${s.length} 条记录`)
}

function openDetail(img) {
  selectedId.value = img.id
  detailTab.value = 'result'
  mainTab.value = 'detail'
  schemeGenerated.value = false
  aiScheme.value = ''
}

async function generateScheme() {
  if (!selected.value) return
  const settings = JSON.parse(localStorage.getItem('advisor_settings') || '{}')
  if (!settings.apiKey) { ElMessage.warning('请先在农事顾问页面配置 API Key'); return }
  schemeLoading.value = true
  try {
    const r = selected.value.result
    const prompt = `作为农业专家，请为以下诊断结果生成详细、真实可操作的治理方案：

诊断信息：
- 病害名称：${r.fine_label || r.coarse_label}
- 问题类别：${r.coarse_label}
- 严重程度：${SEV[r.severity] || r.severity}
- 置信度：${Math.round(r.confidence * 100)}%

请按以下格式给出治理方案（用中文回答，内容要具体、专业、可操作）：
【诊断确认】确认病害及病因分析
【推荐用药】药剂名称、稀释倍数、施用方法、频率
【绿色减药方案】生物防治、物理防治等环保方案
【施肥建议】针对性的施肥调整建议
【预防措施】后续预防要点
【注意事项】安全间隔期、用药禁忌等`
    const res = await api.chatCompletions({
      messages: [{ role: 'user', content: prompt }],
      api_key: settings.apiKey,
      model: settings.textModel || 'glm-4-flash',
    })
    aiScheme.value = res.content
    schemeGenerated.value = true
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message || '未知错误'))
  } finally {
    schemeLoading.value = false
  }
}

async function submitApproved() {
  const approved = images.value.filter(i => i.status === 'approved' && i.result)
  if (!approved.length) { ElMessage.warning('没有审核通过的记录'); return }
  submitting.value = true
  let count = 0
  for (const img of approved) {
    try {
      const fd = new FormData()
      fd.append('image_path', img.result.image_url.replace('/uploads/', ''))
      fd.append('user_id', '1')
      fd.append('coarse_category', img.result.coarse_category)
      fd.append('fine_class', img.result.fine_class || '')
      fd.append('confidence', img.result.confidence)
      fd.append('severity', img.result.severity)
      fd.append('detection_boxes', JSON.stringify(img.result.detection_boxes || []))
      fd.append('scheme', JSON.stringify(img.result.scheme || {}))
      fd.append('rag_advice', img.result.rag_advice || '')
      await api.storeDiagnosis(fd)
      count++
      img.status = 'stored'
    } catch {}
  }
  submitting.value = false
  ElMessage.success(`已存储 ${count} 条诊断记录`)
  if (count) router.push('/history')
}

const reporting = ref(false)

/* 取图片的数据 URL：优先用本地 File；
   刷新后恢复的记录没有 File，改为拉取后端地址再转 base64，保证导出的 HTML 离线可看图 */
function imageToDataUrl(img) {
  const readAsDataUrl = (source, fallback) => new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => resolve(fallback)
    reader.readAsDataURL(source)
  })
  if (img.file) return readAsDataUrl(img.file, img.url || '')
  return fetch(img.url)
    .then(r => r.blob())
    .then(blob => readAsDataUrl(blob, img.url || ''))
    .catch(() => img.url || '')
}

async function generateReport() {
  const targets = selectedList.value.length ? selectedList.value : doneList.value
  if (!targets.length) { ElMessage.warning('没有可生成报告的检测结果'); return }
  reporting.value = true
  try {
    let itemsHtml = ''
    for (const img of targets) {
      const r = img.result
      const conf = Math.round(r.confidence * 100)
      const sev = SEV[r.severity] || r.severity
      const boxes = []
      ;(r.detection_boxes || []).forEach((b, idx) => {
        const x1 = (b.x1 ?? b.x) ?? 0
        const y1 = (b.y1 ?? b.y) ?? 0
        const x2 = (b.x2 ?? ((b.x ?? 0) + (b.width ?? 0))) ?? 0
        const y2 = (b.y2 ?? ((b.y ?? 0) + (b.height ?? 0))) ?? 0
        boxes.push(`框${idx + 1}: (${Math.round(x1)}, ${Math.round(y1)}) → (${Math.round(x2)}, ${Math.round(y2)})`)
      })
      const imgB64 = await imageToDataUrl(img)
      itemsHtml += `
      <section class="item">
        <h2>${r.fine_label || r.coarse_label} · ${sev}</h2>
        <img src="${imgB64}" alt="样本图片" />
        <div class="meta">
          <p><span>问题类别：</span>${r.coarse_label}</p>
          <p><span>细分类别：</span>${r.fine_label || '—'}</p>
          <p><span>置信度：</span>${conf}%</p>
          <p><span>严重程度：</span>${sev}</p>
          <p><span>检测框：</span>${boxes.join('；') || '无'}</p>
        </div>
      </section>`
    }
    const now = new Date().toLocaleString('zh-CN')
    const summary = `共 ${targets.length} 份样本，其中严重 ${targets.filter(i => (i.result.severity) === 'severe').length} 份、中度 ${targets.filter(i => i.result.severity === 'moderate').length} 份、轻度 ${targets.filter(i => i.result.severity === 'mild').length} 份`
    const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>农作物病虫害批量诊断报告</title>
<style>
  body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 800px; margin: 0 auto; padding: var(--space-3); color: #1f2937; }
  h1 { color: #059669; border-bottom: 2px solid #059669; padding-bottom: 12px; }
  .sub { color: #6b7280; font-size: 14px; margin: 8px 0 24px; }
  .item { border: 1px solid #e5e7eb; border-radius: 12px; padding: var(--space-3); margin-bottom: 20px; page-break-inside: avoid; }
  .item h2 { margin: 0 0 12px; font-size: 18px; color: #111827; }
  .item img { max-width: 100%; max-height: 320px; border-radius: 8px; display: block; margin-bottom: 12px; }
  .meta p { margin: 4px 0; font-size: 14px; line-height: 1.6; }
  .meta span { color: #6b7280; display: inline-block; min-width: 80px; }
</style>
</head>
<body>
<h1>农作物病虫害批量诊断报告</h1>
<p class="sub">智农慧眼 AgriEye · 生成时间：${now} · ${summary}</p>
${itemsHtml}
</body>
</html>`
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `农作物病虫害诊断报告_${Date.now()}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success(`已生成 ${targets.length} 份样本的诊断报告`)
  } catch (e) {
    ElMessage.error('报告生成失败：' + (e.message || '未知错误'))
  } finally {
    reporting.value = false
  }
}

function clearAll() {
  images.value.forEach(i => URL.revokeObjectURL(i.url))
  images.value = []
  detecting.value = false
  detectProgress.value = 0
  selectedId.value = ''
  mainTab.value = 'review'
  aiScheme.value = ''
  schemeGenerated.value = false
  clearSession()
}

/* ============ 会话保持：切换页面(由 KeepAlive 保) + 刷新页面(localStorage 保) ============ */
const LS_KEY = 'agrieye_recognize_session_v1'

function persistSession() {
  try {
    // 仅持久化已检测项：其 result.image_url 是后端地址，刷新后仍可访问；
    // 未检测项只有本地 blob URL（刷新即失效）且 File 无法序列化，故不保存。
    const data = images.value
      .filter(i => i.result)
      .map(i => ({ id: i.id, status: i.status, selected: i.selected, result: i.result }))
    localStorage.setItem(LS_KEY, JSON.stringify({
      images: data, selectedId: selectedId.value, mainTab: mainTab.value,
      aiScheme: aiScheme.value, schemeGenerated: schemeGenerated.value,
    }))
  } catch { /* 容量超限或隐私模式，静默忽略 */ }
}

function restoreSession() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return
    const d = JSON.parse(raw)
    const list = (d.images || []).map(i => ({
      id: i.id, file: null, url: i.result?.image_url || '',
      status: i.status, result: i.result, selected: !!i.selected,
    }))
    if (!list.length) { localStorage.removeItem(LS_KEY); return }
    images.value = list
    selectedId.value = list.some(i => i.id === d.selectedId) ? d.selectedId : list[0].id
    mainTab.value = d.mainTab || 'review'
    aiScheme.value = d.aiScheme || ''
    schemeGenerated.value = !!d.schemeGenerated
  } catch {
    localStorage.removeItem(LS_KEY)  // 数据损坏则丢弃，避免反复报错
  }
}

function clearSession() { try { localStorage.removeItem(LS_KEY) } catch { /* ignore */ } }

onMounted(restoreSession)
watch([images, selectedId, aiScheme, schemeGenerated, mainTab], persistSession, { deep: true })

onBeforeUnmount(() => { images.value.forEach(i => URL.revokeObjectURL(i.url)) })
</script>

<template>
  <div class="recognize-page">
    <div class="main-grid">
      <!-- 左：胶片条上传预览 -->
      <div class="left-col">
        <div class="card upload-card">
          <input type="file" ref="fileInput" accept="image/*" multiple @change="onFilesChange" class="file-input" />

          <div class="upload-zone" v-if="!images.length" @drop="onDrop" @dragover.prevent @click="triggerUpload">
            <div class="upload-content">
              <div class="upload-icon"><Upload :size="44" /></div>
              <h3 class="upload-title">点击或拖拽上传多张图片</h3>
              <p class="upload-hint">支持 JPG / PNG / WEBP · 可多选 · 单张 ≤ 10MB</p>
            </div>
          </div>

          <template v-else>
            <div class="img-toolbar">
              <span class="img-count"><span class="dot live"></span> 已上传 {{ images.length }} 张</span>
              <div class="img-actions">
                <button class="img-action-btn" @click="triggerUpload"><ImagePlus :size="15" /> 继续上传</button>
                <button class="img-action-btn danger" @click="clearAll" :disabled="detecting"><Trash2 :size="15" /> 清除全部</button>
              </div>
            </div>

            <!-- 胶片条 -->
            <div class="film-strip">
              <div class="film-frame" v-for="(img, i) in images" :key="img.id"
                :class="{ active: img.id === selectedId, [img.status]: true }" @click="openDetail(img)">
                <span class="frame-no">{{ String(i + 1).padStart(2, '0') }}</span>
                <img :src="img.url" />
                <span class="frame-pip" :class="img.status"></span>
                <button class="frame-del" @click.stop="removeImage(img.id)"><X :size="12" /></button>
              </div>
            </div>

            <div class="detect-section">
              <button class="detect-btn" @click="detectAll" :disabled="detecting || !hasPending">
                <Loader2 v-if="detecting" :size="18" class="animate-spin" />
                <ScanSearch v-else :size="18" />
                {{ detecting ? `AI 检测中 ${detectProgress}%` : '开始批量检测' }}
              </button>
              <div class="progress-bar" v-if="detecting">
                <div class="progress-fill" :style="{ width: detectProgress + '%' }"></div>
              </div>
              <p class="detect-hint" v-if="!hasPending && doneList.length">全部样本已检测，可审核或重新上传</p>
            </div>
          </template>
        </div>

        <!-- 能力说明条 -->
        <div class="card info-card">
          <div class="info-item"><Cpu :size="18" /><div><strong>多模态识别</strong><span>23 类细分 · 4 大病害域</span></div></div>
          <div class="info-item"><ShieldCheck :size="18" /><div><strong>人工审核</strong><span>逐条确认后入库</span></div></div>
          <div class="info-item"><Database :size="18" /><div><strong>可追溯</strong><span>档案全程留痕</span></div></div>
        </div>
      </div>

      <!-- 右：审核控制台 -->
      <div class="right-col">
        <div class="card review-card">
          <div class="tabs">
            <button class="tab" :class="{ active: mainTab === 'review' }" @click="mainTab = 'review'">
              审核列表
              <span class="tab-count" v-if="doneList.length">{{ doneList.length }}</span>
            </button>
            <button class="tab" :class="{ active: mainTab === 'detail' }" @click="mainTab = 'detail'" :disabled="!selected">
              结果详情
            </button>
          </div>

          <!-- 审核流水线 -->
          <div class="pipeline" v-if="selected">
            <div class="pipe-track">
              <div class="pipe-step" v-for="(s, i) in STAGES" :key="s"
                :class="{ done: i <= stageState.stage && !stageState.rejected, active: i === stageState.stage && !stageState.rejected }">
                <span class="pipe-dot">
                  <Check :size="12" v-if="i < stageState.stage && !stageState.rejected" />
                </span>
                <span class="pipe-label">{{ s }}</span>
              </div>
            </div>
            <div class="pipe-flag" v-if="stageState.rejected"><XCircle :size="13" /> 已拒绝</div>
            <div class="pipe-flag err" v-else-if="stageState.error"><AlertCircle :size="13" /> 检测失败</div>
          </div>

          <template v-if="mainTab === 'review'">
            <div class="bulk-toolbar" v-if="doneList.length">
              <el-checkbox :model-value="allChecked" :indeterminate="indeterminate" @change="toggleSelectAll">全选</el-checkbox>
              <span class="bulk-count" v-if="selectedList.length">已选 {{ selectedList.length }} 项</span>
              <div class="bulk-btns">
                <button class="bulk-btn approve" @click="batchApprove"><CheckCheck :size="15" />通过</button>
                <button class="bulk-btn reject" @click="batchReject"><XCircle :size="15" />拒绝</button>
                <button class="bulk-btn report" @click="generateReport"><FileDown :size="15" />报告</button>
                <button class="bulk-btn del" @click="batchDelete"><Trash2 :size="15" />删除</button>
              </div>
            </div>

            <div class="result-list" v-if="doneList.length">
              <div class="result-item" v-for="img in doneList" :key="img.id"
                :class="{ approved: img.status === 'approved', rejected: img.status === 'rejected', stored: img.status === 'stored', active: img.id === selectedId }"
                @click="openDetail(img)">
                <el-checkbox :model-value="img.selected" @change="img.selected = $event" @click.stop />
                <div class="result-thumb">
                  <img :src="img.result.image_url" />
                </div>
                <div class="result-info">
                  <div class="result-name">{{ img.result.fine_label || img.result.coarse_label }}</div>
                  <div class="result-meta">
                    <span class="meta-conf">{{ Math.round(img.result.confidence * 100) }}%</span>
                    <span class="sev-chip" :class="img.result.severity">{{ SEV[img.result.severity] || img.result.severity }}</span>
                    <span class="mode-badge" :class="modeClass(img.result.mode)">{{ modeText(img.result.mode) }}</span>
                  </div>
                </div>
                <div class="review-actions" v-if="['done','approved','rejected'].includes(img.status)" @click.stop>
                  <button class="review-btn approve" :class="{ active: img.status === 'approved' }" @click="approve(img)"><Check :size="14" /></button>
                  <button class="review-btn reject" :class="{ active: img.status === 'rejected' }" @click="reject(img)"><XCircle :size="14" /></button>
                </div>
              </div>
            </div>

            <div class="empty-state" v-else>
              <div class="empty-icon"><ScanSearch :size="44" /></div>
              <h3>暂无检测结果</h3>
              <p>上传图片并点击「开始批量检测」，结果将显示在此处</p>
              <div class="empty-steps">
                <div class="step"><span class="step-num">1</span>上传</div>
                <div class="step"><span class="step-num">2</span>检测</div>
                <div class="step"><span class="step-num">3</span>审核</div>
              </div>
            </div>

            <div class="submit-area" v-if="approvedCount > 0">
              <button class="submit-btn" @click="submitApproved" :disabled="submitting">
                <Loader2 v-if="submitting" :size="16" class="animate-spin" />
                <FileCheck2 v-else :size="16" />
                一键存入（{{ approvedCount }} 条通过{{ storedCount ? ` · 已入库 ${storedCount}` : '' }}）
              </button>
            </div>
          </template>

          <!-- 结果详情 -->
          <template v-else-if="selected">
            <div class="detail-tabs">
              <button class="dtab" :class="{ active: detailTab === 'result' }" @click="detailTab = 'result'">检测结果</button>
              <button class="dtab" :class="{ active: detailTab === 'scheme' }" @click="detailTab = 'scheme'">智能治理方案</button>
            </div>

            <div class="detail-body" v-if="detailTab === 'result'">
              <div class="preview-container">
                <DetectionCanvas
                  :image-url="selected.result.image_url"
                  :boxes="selected.result.detection_boxes || []"
                  :category="selected.result.coarse_category"
                  :label="selected.result.fine_label || selected.result.coarse_label"
                  :max-height="340" />
              </div>
              <div class="detail-stats">
                <div class="detail-mode">
                  <span class="mode-badge lg" :class="modeClass(selected.result.mode)">{{ modeText(selected.result.mode) }}</span>
                </div>
                <ConfidenceRing :value="selected.result.confidence" :accent="selected.result.confidence >= 0.8 ? 'accent' : selected.result.confidence >= 0.5 ? 'warning' : 'danger'" label="置信度" />
                <div class="stat-grid">
                  <div class="stat-row"><span class="stat-key">检测数量</span><span class="stat-val">{{ (selected.result.detection_boxes || []).length }} 个</span></div>
                  <div class="stat-row"><span class="stat-key">问题类别</span><span class="stat-val">{{ selected.result.coarse_label }}</span></div>
                  <div class="stat-row"><span class="stat-key">细分类别</span><span class="stat-val">{{ selected.result.fine_label }}</span></div>
                  <div class="stat-row"><span class="stat-key">严重程度</span><span class="stat-val sev" :class="selected.result.severity">{{ SEV[selected.result.severity] || selected.result.severity }}</span></div>
                  <div class="stat-row" v-if="selected.result.mode === 'unknown'"><span class="stat-key">提示</span><span class="stat-val">未识别到农作物特征，请上传作物叶片或田间虫害照片</span></div>
                </div>
              </div>
            </div>

            <div class="detail-body" v-else>
              <div class="scheme-section">
                <el-alert :title="`诊断：${selected.result.scheme?.diagnosis || selected.result.fine_label || selected.result.coarse_label}`"
                  :description="selected.result.scheme?.cause || ''" type="info" :closable="false" show-icon class="cause" />

                <div v-if="!schemeGenerated && !schemeLoading" class="scheme-gen-area">
                  <button class="scheme-gen-btn" @click="generateScheme"><Sparkles :size="16" /> 生成 AI 治理方案</button>
                  <p class="scheme-gen-hint">基于智谱大模型生成专业、可落地的治理方案</p>
                </div>

                <div v-if="schemeLoading" class="scheme-loading">
                  <div class="typing"><span></span><span></span><span></span></div>
                  <span>AI 正在生成治理方案…</span>
                </div>

                <MarkdownView v-if="schemeGenerated && aiScheme" :source="aiScheme" class="ai-scheme-text" />
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.recognize-page {
  display: flex;
  flex-direction: column;
  gap: var(--gap-section);
  height: calc(100vh - var(--topbar-height) - var(--content-padding) * 2);
  overflow: hidden;
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: var(--gap-box);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
@media (max-width: 1180px) { .main-grid { grid-template-columns: 1fr 376px; } }
@media (max-width: 1024px) { .main-grid { grid-template-columns: 1fr; } }

.left-col {
  display: flex;
  flex-direction: column;
  gap: var(--gap-box);
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}
.right-col {
  display: flex;
  flex-direction: column;
  gap: var(--gap-box);
  min-height: 0;
  overflow: hidden;
}

.card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* ---------- 上传卡（padding:0，内层区块为唯一间距来源，避免双重 padding） ---------- */
.upload-card { display: flex; flex-direction: column; min-height: 0; padding: 0; }

.upload-zone {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  border: 2px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  margin: var(--space-4);
  cursor: pointer;
  transition: var(--transition);
  background: var(--bg);
}
.upload-zone:hover { border-color: var(--accent); background: var(--accent-soft); }

.file-input { display: none; }
.upload-content { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-3); text-align: center; }
.upload-icon {
  width: 92px; height: 92px; border-radius: var(--radius-xl);
  background: var(--accent-soft); display: flex; align-items: center; justify-content: center; color: var(--accent);
  box-shadow: var(--shadow-accent);
}
.upload-title { font-size: var(--text-lg); font-weight: 700; color: var(--fg); margin: 0; }
.upload-hint { font-size: var(--text-sm); color: var(--fg-subtle); margin: 0; }

.img-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}
.img-count { display: flex; align-items: center; gap: 8px; font-size: var(--text-sm); color: var(--fg-secondary); font-weight: 600; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--fg-subtle); }
.dot.live { background: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.img-actions { display: flex; gap: 8px; }
.img-action-btn {
  display: flex; align-items: center; gap: 6px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-strong); border-radius: var(--radius-md);
  background: var(--bg-elevated); color: var(--fg-secondary);
  font-size: var(--text-xs); font-weight: 600; cursor: pointer; transition: var(--transition);
}
.img-action-btn:hover { border-color: var(--accent); color: var(--accent); }
.img-action-btn.danger:hover { border-color: var(--danger); color: var(--danger); }
.img-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ---------- 胶片条 ---------- */
.film-strip {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 14px; padding: 22px var(--space-4);
}
.film-strip::before {
  content: ''; position: absolute; top: 8px; left: 0; right: 0; height: 6px;
  background-image: radial-gradient(circle, var(--bg-invert) 2px, transparent 2.6px);
  background-size: 15px 6px; background-repeat: repeat-x; opacity: .14;
}
.film-strip::after {
  content: ''; position: absolute; bottom: 8px; left: 0; right: 0; height: 6px;
  background-image: radial-gradient(circle, var(--bg-invert) 2px, transparent 2.6px);
  background-size: 15px 6px; background-repeat: repeat-x; opacity: .14;
}
.film-frame {
  position: relative; width: 100%; aspect-ratio: 1;
  border-radius: var(--radius-md); overflow: hidden;
  border: 2px solid var(--border-strong); cursor: pointer;
  transition: var(--transition);
  background: var(--bg-muted);
}
.film-frame img { width: 100%; height: 100%; object-fit: cover; }
.film-frame.active { border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft), var(--shadow-md); }
.film-frame.detecting { border-color: var(--tech); }
.film-frame.done, .film-frame.approved, .film-frame.stored { border-color: color-mix(in srgb, var(--accent) 55%, var(--border-strong)); }
.film-frame.rejected { border-color: var(--danger); }
.film-frame.error { border-color: var(--danger); }
.frame-no {
  position: absolute; top: 6px; left: 6px; z-index: 2;
  font-family: var(--font-mono); font-size: 10px; font-weight: 700;
  background: rgba(4,20,12,.7); color: var(--fg); padding: 1px 6px; border-radius: var(--radius-sm);
}
.frame-pip {
  position: absolute; bottom: 6px; left: 6px; z-index: 2;
  width: 9px; height: 9px; border-radius: 50%; border: 2px solid rgba(4,20,12,.6);
  background: var(--fg-subtle);
}
.frame-pip.pending { background: var(--fg-subtle); }
.frame-pip.detecting { background: var(--tech); animation: pulse 1.2s infinite; }
.frame-pip.done { background: var(--accent); }
.frame-pip.approved { background: var(--success); }
.frame-pip.stored { background: var(--tech); }
.frame-pip.rejected, .frame-pip.error { background: var(--danger); }
.frame-del {
  position: absolute; bottom: 6px; right: 6px; z-index: 3;
  width: 22px; height: 22px; border-radius: 50%; border: none;
  background: var(--danger); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: var(--transition);
}
.film-frame:hover .frame-del { opacity: 1; }
.frame-del:hover { background: #dc2626; transform: scale(1.1); }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }

.detect-section { padding: var(--space-4); display: flex; flex-direction: column; gap: 10px; border-top: 1px solid var(--border); }
.detect-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; padding: var(--space-3);
  background: var(--accent-gradient); border: none; border-radius: var(--radius-md);
  color: var(--fg-on-accent); font-size: var(--text-base); font-weight: 700;
  cursor: pointer; transition: var(--transition); box-shadow: var(--shadow-accent);
}
.detect-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: var(--shadow-accent-lg); }
.detect-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.progress-bar { height: 4px; background: var(--bg-muted); border-radius: var(--radius-full); overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent-gradient); border-radius: var(--radius-full); transition: width .3s var(--ease-out); }
.detect-hint { font-size: var(--text-xs); color: var(--fg-subtle); margin: 0; text-align: center; }

/* ---------- 能力条 ---------- */
.info-card { display: flex; gap: var(--space-2); padding: var(--space-3); flex-wrap: wrap; }
.info-item { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 120px; padding: var(--space-2); }
.info-item svg { color: var(--accent); flex-shrink: 0; }
.info-item strong { display: block; font-size: var(--text-sm); color: var(--fg); }
.info-item span { font-size: var(--text-xs); color: var(--fg-muted); }

/* ---------- 审核控制台（padding:0，间距由内部区块提供） ---------- */
.review-card { display: flex; flex-direction: column; height: 100%; min-height: 0; padding: 0; }

.tabs { display: flex; gap: 4px; padding: var(--space-3); background: var(--bg-muted); border-radius: var(--radius-md); margin: var(--space-4) var(--space-4) 0; }
.tab {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: var(--space-3); border: none; background: transparent; color: var(--fg-muted);
  font-size: var(--text-sm); font-weight: 600; border-radius: var(--radius-sm); cursor: pointer; transition: var(--transition);
}
.tab.active { background: var(--bg-elevated); color: var(--accent); box-shadow: var(--shadow-sm); }
.tab:disabled { opacity: 0.4; cursor: not-allowed; }
.tab-count { font-size: 11px; background: var(--accent); color: var(--fg-on-accent); border-radius: var(--radius-full); padding: 1px 7px; font-weight: 700; }

/* 流水线 */
.pipeline { display: flex; align-items: center; gap: 8px; padding: var(--space-3) var(--space-4); }
.pipe-track { flex: 1; display: flex; align-items: center; }
.pipe-step { display: flex; align-items: center; gap: 6px; flex: 1; position: relative; }
.pipe-step::after {
  content: ''; flex: 1; height: 2px; margin: 0 4px;
  background: var(--border-strong); transition: var(--transition);
}
.pipe-step:last-child::after { display: none; }
.pipe-step.done::after { background: var(--accent); }
.pipe-dot {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-muted); border: 2px solid var(--border-strong); color: var(--fg-on-accent);
  transition: var(--transition);
}
.pipe-step.active .pipe-dot { border-color: var(--accent); background: var(--accent-soft); box-shadow: 0 0 0 4px var(--accent-soft); }
.pipe-step.done .pipe-dot { background: var(--accent); border-color: var(--accent); }
.pipe-label { font-size: var(--text-xs); font-weight: 600; color: var(--fg-muted); white-space: nowrap; }
.pipe-step.active .pipe-label, .pipe-step.done .pipe-label { color: var(--fg); }
.pipe-flag { display: flex; align-items: center; gap: 4px; font-size: var(--text-xs); font-weight: 600; color: var(--danger); flex-shrink: 0; }
.pipe-flag.err { color: var(--danger); }

.bulk-toolbar { display: flex; align-items: center; gap: 12px; padding: var(--space-3) var(--space-4); background: var(--bg-muted); border-radius: var(--radius-md); margin: var(--space-3) var(--space-4); flex-wrap: wrap; }
.bulk-count { font-size: var(--text-xs); color: var(--fg-muted); }
.bulk-btns { display: flex; gap: 6px; margin-left: auto; }
.bulk-btn {
  display: flex; align-items: center; gap: 4px;
  padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong);
  background: var(--bg-elevated); border-radius: var(--radius-sm);
  font-size: var(--text-xs); font-weight: 600; color: var(--fg-muted); cursor: pointer; transition: var(--transition);
}
.bulk-btn:hover { border-color: var(--accent); color: var(--accent); }
.bulk-btn.approve:hover { border-color: var(--success); color: var(--success); background: var(--accent-soft); }
.bulk-btn.reject:hover { border-color: var(--danger); color: var(--danger); background: color-mix(in srgb, var(--danger) 10%, transparent); }
.bulk-btn.report:hover { border-color: var(--tech); color: var(--tech); background: var(--tech-soft); }
.bulk-btn.del:hover { border-color: var(--danger); color: var(--danger); }

.result-list { display: flex; flex-direction: column; gap: 8px; padding: 0 var(--space-4) var(--space-3); flex: 1; overflow-y: auto; }
.result-item {
  display: flex; align-items: center; gap: 10px; padding: var(--space-3);
  border: 1px solid var(--border); border-radius: var(--radius-md); cursor: pointer; transition: var(--transition);
}
.result-item:hover { border-color: var(--accent); background: var(--bg-hover); }
.result-item.active { border-color: var(--accent); background: var(--accent-soft); }
.result-item.approved { border-color: color-mix(in srgb, var(--success) 55%, var(--border-strong)); background: color-mix(in srgb, var(--success) 6%, transparent); }
.result-item.rejected { opacity: 0.6; border-color: var(--danger); }
.result-item.stored { border-color: color-mix(in srgb, var(--tech) 55%, var(--border-strong)); background: color-mix(in srgb, var(--tech) 6%, transparent); }

.result-thumb { width: 52px; height: 52px; border-radius: var(--radius-md); overflow: hidden; flex-shrink: 0; background: var(--bg-muted); }
.result-thumb img { width: 100%; height: 100%; object-fit: cover; }
.result-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.result-name { font-size: var(--text-sm); font-weight: 700; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.result-meta { display: flex; gap: 8px; align-items: center; }
.meta-conf { font-size: var(--text-xs); font-weight: 700; color: var(--accent); font-variant-numeric: tabular-nums; }

.sev-chip { font-size: 11px; padding: 2px 9px; border-radius: var(--radius-full); font-weight: 600; }
.sev-chip.mild { background: var(--accent-soft); color: var(--accent); }

.mode-badge { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: var(--radius-full); letter-spacing: 0.3px; white-space: nowrap; }
.mode-badge.model { background: var(--accent-soft); color: var(--accent); }
.mode-badge.heuristic { background: color-mix(in srgb, var(--warning) 16%, transparent); color: var(--warning); }
.mode-badge.unknown { background: color-mix(in srgb, var(--danger) 16%, transparent); color: var(--danger); }
.mode-badge.lg { font-size: var(--text-sm); padding: 4px 13px; }
.detail-mode { display: flex; margin-bottom: var(--space-3); }
.detail-mode .mode-badge { font-family: var(--font-ui); }
.sev-chip.moderate { background: color-mix(in srgb, var(--warning) 16%, transparent); color: var(--warning); }
.sev-chip.severe { background: color-mix(in srgb, var(--danger) 16%, transparent); color: var(--danger); }

.review-actions { display: flex; gap: 4px; flex-shrink: 0; }
.review-btn {
  display: flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; border: 1px solid var(--border-strong);
  background: var(--bg-elevated); border-radius: var(--radius-sm);
  color: var(--fg-muted); cursor: pointer; transition: var(--transition);
}
.review-btn.approve:hover, .review-btn.approve.active { border-color: var(--success); color: var(--success); background: var(--accent-soft); }
.review-btn.reject:hover, .review-btn.reject.active { border-color: var(--danger); color: var(--danger); background: color-mix(in srgb, var(--danger) 10%, transparent); }

.empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: var(--space-5) var(--space-4); text-align: center; }
.empty-icon { width: 76px; height: 76px; border-radius: var(--radius-xl); background: var(--accent-soft); display: flex; align-items: center; justify-content: center; color: var(--accent); margin-bottom: var(--space-3); }
.empty-state h3 { font-size: var(--text-lg); color: var(--fg); margin: 0 0 6px; }
.empty-state p { font-size: var(--text-sm); color: var(--fg-muted); margin: 0; }
.empty-steps { display: flex; gap: var(--space-5); margin-top: var(--space-4); }
.step { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: var(--text-xs); color: var(--fg-muted); }
.step-num { width: 28px; height: 28px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); display: flex; align-items: center; justify-content: center; font-weight: 700; }

.submit-area { padding: var(--space-3) var(--space-4) var(--space-4); border-top: 1px solid var(--border); }
.submit-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; padding: var(--space-3);
  background: var(--accent-gradient); border: none; border-radius: var(--radius-md);
  color: var(--fg-on-accent); font-size: var(--text-sm); font-weight: 700; cursor: pointer; transition: var(--transition);
  box-shadow: var(--shadow-accent);
}
.submit-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: var(--shadow-accent-lg); }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.detail-tabs { display: flex; gap: 4px; padding: var(--space-3); background: var(--bg-muted); border-radius: var(--radius-md); margin: var(--space-3) var(--space-4) 0; }
.dtab { flex: 1; padding: var(--space-3); border: none; background: transparent; color: var(--fg-muted); font-size: var(--text-sm); font-weight: 600; border-radius: var(--radius-sm); cursor: pointer; transition: var(--transition); }
.dtab.active { background: var(--bg-elevated); color: var(--accent); box-shadow: var(--shadow-sm); }

.detail-body { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-4); flex: 1; overflow-y: auto; }
.preview-container { border-radius: var(--radius-md); overflow: hidden; background: var(--bg-invert); }
.detail-stats { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-3); background: var(--bg-muted); border-radius: var(--radius-md); }
.stat-grid { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.stat-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--border); }
.stat-row:last-child { border-bottom: none; }
.stat-key { font-size: var(--text-sm); color: var(--fg-muted); }
.stat-val { font-size: var(--text-sm); font-weight: 600; color: var(--fg); font-variant-numeric: tabular-nums; }
.stat-val.sev.mild { color: var(--accent); }
.stat-val.sev.moderate { color: var(--warning); }
.stat-val.sev.severe { color: var(--danger); }

.scheme-section { display: flex; flex-direction: column; gap: var(--space-3); }
.cause { margin-bottom: 2px; }
.scheme-gen-area { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-3); }
.scheme-gen-btn {
  display: flex; align-items: center; gap: 8px;
  padding: var(--space-3) var(--space-5); background: var(--accent-gradient); border: none;
  border-radius: var(--radius-md); color: var(--fg-on-accent); font-size: var(--text-sm); font-weight: 700;
  cursor: pointer; transition: var(--transition); box-shadow: var(--shadow-accent);
}
.scheme-gen-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-accent-lg); }
.scheme-gen-hint { font-size: var(--text-xs); color: var(--fg-subtle); margin: 0; }
.scheme-loading { display: flex; align-items: center; gap: 12px; padding: var(--space-3); color: var(--fg-muted); font-size: var(--text-sm); }
.typing { display: flex; gap: 6px; }
.typing span { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: typing 1.4s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%,60%,100% { opacity: .3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-4px); } }
.ai-scheme-text {
  background: var(--bg-muted); border: 1px solid var(--border); border-left: 3px solid var(--accent);
  border-radius: var(--radius-md); padding: var(--space-4);
}

@media (max-width: 1024px) {
  .recognize-page { height: auto; overflow: visible; }
  .left-col, .right-col { overflow: visible; }
  .review-card { height: auto; }
}
</style>
