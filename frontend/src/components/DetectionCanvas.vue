<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  imageUrl: String,
  boxes: { type: Array, default: () => [] },
  category: String,
  label: { type: String, default: '' },
  maxHeight: { type: Number, default: 440 },
})

const canvas = ref(null)
const imgEl = ref(null)
const loaded = ref(false)

function cssVar(name, fallback) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}
function getCatColor(category) {
  const map = {
    fungal_disease: cssVar('--cat-fungal', '#ea580c'),
    pest: cssVar('--cat-pest', '#dc2626'),
    deficiency: cssVar('--cat-deficiency', '#ca8a04'),
    phytotoxicity: cssVar('--cat-phytotoxicity', '#7c3aed'),
  }
  return map[category] || cssVar('--accent', '#16a34a')
}

function draw() {
  if (!canvas.value || !imgEl.value || !loaded.value) return
  const img = imgEl.value
  const c = canvas.value
  const w = img.clientWidth, h = img.clientHeight
  if (w === 0 || h === 0) return
  c.width = w
  c.height = h
  c.style.width = w + 'px'
  c.style.height = h + 'px'
  const ctx = c.getContext('2d')
  ctx.clearRect(0, 0, w, h)
  const sx = w / img.naturalWidth, sy = h / img.naturalHeight
  const color = getCatColor(props.category)
  const text = props.label || '检测目标'
  props.boxes.forEach((b) => {
    const x1 = (b.x1 ?? b.x) ?? 0
    const y1 = (b.y1 ?? b.y) ?? 0
    const x2 = (b.x2 ?? (((b.x ?? 0) + (b.width ?? 0)))) ?? 0
    const y2 = (b.y2 ?? (((b.y ?? 0) + (b.height ?? 0)))) ?? 0
    const x = x1 * sx, y = y1 * sy, bw = (x2 - x1) * sx, bh = (y2 - y1) * sy
    if (bw < 1 || bh < 1) return
    ctx.strokeStyle = color
    ctx.lineWidth = Math.max(2, w / 300)
    ctx.setLineDash([])
    ctx.strokeRect(x, y, bw, bh)
    const fontSize = Math.max(12, w / 40)
    ctx.font = "600 " + fontSize + "px 'PingFang SC', 'Microsoft YaHei', sans-serif"
    const tw = ctx.measureText(text).width + fontSize * 1.2
    const labelH = fontSize + 8
    const labelY = y < labelH ? y + 2 : y - labelH
    ctx.fillStyle = color
    ctx.fillRect(x, labelY, tw, labelH)
    ctx.fillStyle = cssVar('--fg-on-accent', '#fff')
    ctx.fillText(text, x + fontSize * 0.6, labelY + fontSize + 2)
  })
}

function onImgLoad() { loaded.value = true; nextTick(draw) }
onMounted(() => window.addEventListener('resize', draw))
onBeforeUnmount(() => window.removeEventListener('resize', draw))
watch(() => props.boxes, () => nextTick(draw), { deep: true })
watch(() => props.imageUrl, () => { loaded.value = false })
watch(() => props.label, () => nextTick(draw))
</script>

<template>
  <div class="detection-canvas">
    <img ref="imgEl" :src="imageUrl" @load="onImgLoad" crossorigin="anonymous" />
    <canvas ref="canvas" class="overlay"></canvas>
  </div>
</template>

<style scoped>
.detection-canvas { position: relative; display: inline-block; border-radius: var(--radius-lg); overflow: hidden; background: var(--bg-invert); line-height: 0; }
.detection-canvas img { display: block; max-width: 100%; max-height: v-bind(maxHeight + 'px'); object-fit: contain; }
.overlay { position: absolute; top: 0; left: 0; pointer-events: none; }
</style>