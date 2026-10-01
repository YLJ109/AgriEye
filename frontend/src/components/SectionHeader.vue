<script setup>
import AppIcon from '@/components/AppIcon.vue'

defineProps({
  title: String,
  subtitle: String,
  icon: String,
  index: { type: [String, Number], default: '' },
  action: String,
})
defineEmits(['action'])
</script>

<template>
  <div class="section-header">
    <div class="sh-left">
      <div class="sh-bar"></div>
      <div v-if="icon" class="sh-icon">
        <AppIcon :name="icon" :size="20" />
      </div>
      <div class="sh-text">
        <div class="sh-title-row">
          <span v-if="index" class="sh-index">{{ index }}</span>
          <h2 class="sh-title">{{ title }}</h2>
        </div>
        <p class="sh-subtitle" v-if="subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <el-button v-if="action" text type="primary" @click="$emit('action')">{{ action }}</el-button>
  </div>
</template>

<style scoped>
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.sh-left { display: flex; align-items: center; gap: var(--space-3); }
.sh-bar { width: 4px; height: 26px; border-radius: var(--radius-full); background: var(--accent-gradient); flex-shrink: 0; }
.sh-icon {
  width: 40px; height: 40px; border-radius: var(--radius-md);
  background: var(--accent-soft); display: flex; align-items: center; justify-content: center;
  color: var(--accent); flex-shrink: 0;
}
.sh-title-row { display: flex; align-items: center; gap: var(--space-2); }
.sh-index {
  font-family: var(--font-mono); font-size: var(--text-xs); font-weight: 700;
  color: var(--accent); background: var(--accent-soft);
  padding: 2px 8px; border-radius: var(--radius-sm); letter-spacing: 0.5px;
}
.sh-title { font-family: var(--font-display); font-size: var(--text-xl); font-weight: var(--weight-bold); letter-spacing: -0.02em; }
.sh-subtitle { color: var(--fg-muted); font-size: var(--text-sm); margin-top: 3px; }
</style>
