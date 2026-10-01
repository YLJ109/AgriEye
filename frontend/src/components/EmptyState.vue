<script setup>
import AppIcon from '@/components/AppIcon.vue'

defineProps({
  icon: { type: String, default: 'folder' },
  title: { type: String, default: '暂无数据' },
  description: String,
  actionText: String,
})
defineEmits(['action'])
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon animate-float">
      <AppIcon :name="icon" :size="48" />
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc" v-if="description">{{ description }}</p>
    <el-button v-if="actionText" type="primary" @click="$emit('action')">{{ actionText }}</el-button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: var(--space-3) var(--space-4); text-align: center;
}
.empty-icon { margin-bottom: 10px; opacity: 0.6; color: var(--fg-muted); }
.empty-title { font-size: var(--text-lg); color: var(--fg-secondary); margin-bottom: var(--space-2); }
.empty-desc { color: var(--fg-muted); font-size: var(--text-sm); margin-bottom: 10px; max-width: 360px; }
</style>