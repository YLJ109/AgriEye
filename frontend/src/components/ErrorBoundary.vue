<script setup>
import { ref, onErrorCaptured } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import AppIcon from '@/components/AppIcon.vue'

const error = ref(null)

onErrorCaptured((err) => {
  error.value = err
  return false
})

function retry() {
  error.value = null
}
</script>

<template>
  <div v-if="error" class="error-boundary">
    <div class="error-card">
      <div class="error-icon">
        <AppIcon name="warning" :size="48" />
      </div>
      <h2 class="error-title">页面渲染出错</h2>
      <p class="error-desc">{{ error.message || '组件加载失败，请重试' }}</p>
      <el-button type="primary" :icon="RefreshCw" @click="retry">重试</el-button>
    </div>
  </div>
  <slot v-else />
</template>

<style scoped>
.error-boundary {
  display: flex; align-items: center; justify-content: center;
  min-height: 400px; padding: var(--space-3);
}
.error-card {
  text-align: center; max-width: 400px;
  padding: var(--space-3);
  background: var(--bg-elevated); border: 1px solid var(--border);
  border-radius: var(--radius-xl); box-shadow: var(--shadow-lg);
}
.error-icon { margin-bottom: 10px; color: var(--warning); display: flex; justify-content: center; }
.error-title {
  font-family: var(--font-display); font-size: var(--text-xl);
  font-weight: var(--weight-bold); color: var(--fg); margin-bottom: var(--space-2);
}
.error-desc {
  font-size: var(--text-sm); color: var(--fg-muted);
  margin-bottom: 10px; line-height: var(--leading-relaxed);
}
</style>