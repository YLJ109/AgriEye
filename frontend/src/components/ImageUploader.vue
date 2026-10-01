<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { Upload, Camera, Image as ImageIcon } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  modelValue: { type: [File, String], default: null },
  loading: { type: Boolean, default: false },
  previewUrl: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'submit'])

const dragOver = ref(false)
const inputRef = ref(null)
const localPreview = ref('')

const file = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const preview = computed(() => props.previewUrl || localPreview.value)

function revokePreview() {
  if (localPreview.value) {
    URL.revokeObjectURL(localPreview.value)
    localPreview.value = ''
  }
}

function handleFile(f) {
  if (!f) return
  if (!f.type.startsWith('image/')) { ElMessage.error('请上传图片文件'); return }
  if (f.size > 10 * 1024 * 1024) { ElMessage.error('图片不能超过 10MB'); return }
  revokePreview()
  file.value = f
  localPreview.value = URL.createObjectURL(f)
  emit('submit', f)
}
function onDrop(e) { dragOver.value = false; handleFile(e.dataTransfer.files[0]) }
function onPick(e) { handleFile(e.target.files[0]); e.target.value = '' }
function reset() { revokePreview(); file.value = null; emit('update:modelValue', null) }

onBeforeUnmount(revokePreview)
</script>

<template>
  <div class="uploader">
    <input type="file" accept="image/*" capture="environment" @change="onPick" ref="inputRef" class="hidden" />

    <div v-if="!preview && !loading"
      class="dropzone" :class="{ dragover }"
      @dragover.prevent="dragOver = true" @dragleave="dragOver = false" @drop.prevent="onDrop"
      @click="inputRef?.click()">
      <div class="dz-icon"><el-icon><Upload /></el-icon></div>
      <h3 class="dz-title">拖拽图片到此处，或点击上传</h3>
      <p class="dz-hint">拍摄作物叶片 · 支持 JPG / PNG / WEBP · 最大 10MB</p>
      <div class="dz-actions">
        <el-button type="primary" @click.stop="inputRef?.click()"><el-icon><Camera /></el-icon>&nbsp;拍照识别</el-button>
        <el-button @click.stop="inputRef?.click()"><el-icon><ImageIcon /></el-icon>&nbsp;选择文件</el-button>
      </div>
      <div class="dz-tips">
        <AppIcon name="bulb" :size="14" />
        <span>聚焦病斑区域，光线均匀效果更佳</span>
      </div>
    </div>

    <div v-else-if="loading" class="loading-zone">
      <div class="scan-frame">
        <div class="scan-line"></div>
        <div class="scan-corner tl"></div><div class="scan-corner tr"></div>
        <div class="scan-corner bl"></div><div class="scan-corner br"></div>
      </div>
      <h3>AI 识别分析中</h3>
      <p>正在提取特征 · 分类判别 · 生成方案…</p>
      <div class="progress-bar"><div class="progress-fill"></div></div>
    </div>

    <div v-else class="preview-zone">
      <img :src="preview" alt="预览" />
      <div class="preview-overlay">
        <el-button class="reset-btn" @click="reset">重新上传</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hidden { display: none; }

.dropzone {
  border: 2px dashed var(--border-strong); border-radius: var(--radius-xl);
  padding: var(--space-3) var(--space-3); text-align: center; cursor: pointer;
  background: var(--bg-elevated); transition: var(--transition);
}
.dropzone:hover, .dropzone.dragover {
  border-color: var(--accent); background: var(--accent-soft);
}
.dz-icon { font-size: 48px; color: var(--accent); margin-bottom: 10px; }
.dz-title { font-size: var(--text-lg); margin-bottom: var(--space-2); }
.dz-hint { color: var(--fg-muted); font-size: var(--text-sm); margin-bottom: 10px; }
.dz-actions { display: flex; gap: var(--space-2); justify-content: center; margin-bottom: 10px; }
.dz-tips { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: var(--text-xs); color: var(--fg-subtle); }

.loading-zone {
  padding: var(--space-3); text-align: center; border-radius: var(--radius-xl);
  background: var(--bg-elevated); border: 1px solid var(--border);
}
.scan-frame {
  width: 120px; height: 120px; margin: 0 auto 10px; position: relative;
  border-radius: var(--radius-md); overflow: hidden; background: var(--bg-muted);
}
.scan-line {
  position: absolute; left: 0; right: 0; height: 3px;
  background: var(--accent);
  animation: scan 2s ease-in-out infinite;
}
@keyframes scan { 0%, 100% { top: 0; } 50% { top: calc(100% - 3px); } }
.scan-corner { position: absolute; width: 20px; height: 20px; border: 3px solid var(--accent); }
.scan-corner.tl { top: 0; left: 0; border-right: none; border-bottom: none; border-radius: 4px 0 0 0; }
.scan-corner.tr { top: 0; right: 0; border-left: none; border-bottom: none; border-radius: 0 4px 0 0; }
.scan-corner.bl { bottom: 0; left: 0; border-right: none; border-top: none; border-radius: 0 0 0 4px; }
.scan-corner.br { bottom: 0; right: 0; border-left: none; border-top: none; border-radius: 0 0 4px 0; }
.loading-zone h3 { color: var(--accent); margin-bottom: var(--space-2); }
.loading-zone p { color: var(--fg-muted); font-size: var(--text-sm); margin-bottom: 10px; }
.progress-bar { width: 240px; height: 4px; background: var(--bg-muted); border-radius: var(--radius-full); margin: 0 auto; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent); border-radius: var(--radius-full); animation: indeterminate 1.5s ease-in-out infinite; }
@keyframes indeterminate { 0% { width: 30%; margin-left: -30%; } 100% { width: 30%; margin-left: 100%; } }

.preview-zone { position: relative; border-radius: var(--radius-xl); overflow: hidden; border: 1px solid var(--border); }
.preview-zone img { width: 100%; max-height: 440px; object-fit: contain; background: var(--bg-invert); }
.preview-overlay { position: absolute; inset: 0; background: linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, transparent 20%, transparent 80%, rgba(0,0,0,0.3) 100%); pointer-events: none; }
.reset-btn { position: absolute; top: var(--space-3); right: var(--space-3); pointer-events: auto; }
</style>