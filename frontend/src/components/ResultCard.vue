<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import CategoryBadge from '@/components/CategoryBadge.vue'
import AppIcon from '@/components/AppIcon.vue'
import MarkdownView from '@/components/MarkdownView.vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const props = defineProps({ result: { type: Object, default: null } })

const SEV = {
  mild: { label: '轻度', color: 'var(--success)', desc: '以预防为主，加强田间管理' },
  moderate: { label: '中度', color: 'var(--warning)', desc: '按方案处置并 7 天后复查' },
  severe: { label: '重度', color: 'var(--danger)', desc: '立即处置并持续观察，大面积发生上报农技部门' },
  none: { label: '—', color: 'var(--fg-muted)', desc: '未识别到农作物特征' },
}
const sev = computed(() => SEV[props.result?.severity] || SEV.none)
const scheme = computed(() => props.result?.scheme || {})
const conf = computed(() => Math.round((props.result?.confidence || 0) * 100))

const aiScheme = ref('')
const schemeLoading = ref(false)
const schemeGenerated = ref(false)

async function generateAiScheme() {
  const settings = JSON.parse(localStorage.getItem('advisor_settings') || '{}')
  if (!settings.apiKey) {
    ElMessage.warning('请先在农事顾问页面配置 API Key')
    return
  }
  schemeLoading.value = true
  try {
    const prompt = `作为农业专家，请为以下诊断结果生成详细、真实可操作的治理方案：

诊断信息：
- 病害名称：${props.result.fine_label || props.result.coarse_label}
- 问题类别：${props.result.coarse_label}
- 严重程度：${sev.value.label}
- 置信度：${conf.value}%
- 作物：${scheme.value.crop || '通用作物'}

请按以下格式给出治理方案（用中文回答，内容要具体、专业、可操作）：

【诊断确认】
确认病害及病因分析

【推荐用药】
药剂名称、稀释倍数、施用方法、频率

【绿色减药方案】
生物防治、物理防治等环保方案

【施肥建议】
针对性的施肥调整建议

【预防措施】
后续预防要点

【注意事项】
安全间隔期、用药禁忌等`
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

const gaugeWidth = ref(104)
function updateGaugeWidth() { gaugeWidth.value = window.innerWidth < 768 ? 88 : 104 }
onMounted(() => { updateGaugeWidth(); window.addEventListener('resize', updateGaugeWidth) })
onBeforeUnmount(() => window.removeEventListener('resize', updateGaugeWidth))
</script>

<template>
  <div class="result" v-if="result">
    <div class="summary card">
      <div class="summary-main">
        <CategoryBadge :category="result.coarse_category" size="lg" />
        <h2 class="fine-name">{{ result.fine_label || result.coarse_label }}</h2>
        <div class="meta">
          <el-tag :type="result.severity === 'severe' ? 'danger' : result.severity === 'moderate' ? 'warning' : 'success'" effect="dark" round>
            {{ sev.label }}危害
          </el-tag>
          <span class="crop" v-if="scheme.crop">{{ scheme.crop }}</span>
          <span class="time">{{ new Date(result.created_at).toLocaleString('zh-CN') }}</span>
        </div>
      </div>
      <div class="conf-gauge">
        <el-progress type="dashboard" :percentage="conf" color="var(--accent)" :width="gaugeWidth" :stroke-width="8">
          <template #default>
            <div class="gauge-inner">
              <strong>{{ conf }}%</strong>
              <span>置信度</span>
            </div>
          </template>
        </el-progress>
      </div>
    </div>

    <div class="card scheme-card">
      <h3 class="block-title"><AppIcon name="clipboard" :size="20" /> 智能治理方案</h3>

      <el-alert :title="`诊断：${scheme.diagnosis || result.fine_label || result.coarse_label}`"
        :description="scheme.cause || ''" type="info" :closable="false" show-icon class="cause" />

      <div v-if="!schemeGenerated && !schemeLoading" class="scheme-gen-area">
        <button class="scheme-gen-btn" @click="generateAiScheme">
          <AppIcon name="sparkles" :size="18" /> 生成 AI 治理方案
        </button>
        <p class="scheme-gen-hint">点击按钮，通过智谱大模型生成专业、详细的治理方案</p>
      </div>

      <div v-if="schemeLoading" class="scheme-loading">
        <div class="typing"><span></span><span></span><span></span></div>
        <span>AI 正在生成治理方案…</span>
      </div>

      <div v-if="schemeGenerated && aiScheme" class="ai-scheme">
        <MarkdownView :source="aiScheme" class="ai-scheme-text" />
        <button class="scheme-regen-btn" @click="generateAiScheme">
          <AppIcon name="refresh" :size="14" /> 重新生成
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result { display: flex; flex-direction: column; gap: 10px; animation: fadeInUp 0.5s var(--ease-out) both; }

.summary { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.summary-main { flex: 1; }
.fine-name { font-size: var(--text-2xl); margin: var(--space-2) 0; }
.meta { display: flex; align-items: center; gap: var(--space-2); color: var(--fg-muted); font-size: var(--text-sm); }
.conf-gauge { flex-shrink: 0; }
.gauge-inner { display: flex; flex-direction: column; align-items: center; }
.gauge-inner strong { font-family: var(--font-display); font-size: var(--text-xl); color: var(--accent); }
.gauge-inner span { font-size: var(--text-xs); color: var(--fg-muted); }

.block-title { font-family: var(--font-display); font-size: var(--text-lg); font-weight: var(--weight-semibold); margin-bottom: 10px; display: flex; align-items: center; gap: var(--space-2); color: var(--fg); }
.cause { margin-bottom: 10px; }

.scheme-gen-area { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-4); }
.scheme-gen-btn { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-6); background: var(--accent); border: none; border-radius: var(--radius-md); color: var(--fg-on-accent); font-size: var(--text-md); font-weight: 600; cursor: pointer; transition: var(--transition); box-shadow: var(--shadow-accent); }
.scheme-gen-btn:hover { background: var(--accent-hover); transform: translateY(-1px); box-shadow: var(--shadow-accent-lg); }
.scheme-gen-hint { font-size: var(--text-xs); color: var(--fg-subtle); }

.scheme-loading { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); color: var(--fg-muted); font-size: var(--text-sm); }
.typing { display: flex; gap: 6px; }
.typing span { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); animation: typing 1.4s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%, 60%, 100% { opacity: 0.3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-4px); } }

.ai-scheme { margin-top: 10px; }
.ai-scheme-text { background: var(--bg-muted); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: var(--radius-md); padding: var(--space-3); }
.scheme-regen-btn { display: flex; align-items: center; gap: 4px; margin-top: var(--space-2); padding: var(--space-3); border: 1px solid var(--border-strong); background: var(--bg-elevated); border-radius: var(--radius-sm); font-size: var(--text-xs); color: var(--fg-muted); cursor: pointer; transition: var(--transition); }
.scheme-regen-btn:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 768px) { .summary { flex-direction: column; } }
</style>