<script setup>
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  category: { type: String, required: true },
  size: { type: String, default: 'md' },
  withIcon: { type: Boolean, default: true },
})

const META = {
  fungal_disease: { label: '真菌病害', color: 'var(--cat-fungal)', soft: 'var(--cat-fungal-soft)', icon: 'fungus' },
  pest: { label: '虫害', color: 'var(--cat-pest)', soft: 'var(--cat-pest-soft)', icon: 'bug' },
  deficiency: { label: '土壤缺肥', color: 'var(--cat-deficiency)', soft: 'var(--cat-deficiency-soft)', icon: 'trendDown' },
  phytotoxicity: { label: '农药药害', color: 'var(--cat-phytotoxicity)', soft: 'var(--cat-phytotoxicity-soft)', icon: 'warning' },
}
const meta = computed(() => META[props.category] || META.fungal_disease)
const iconSize = computed(() => props.size === 'sm' ? 12 : props.size === 'lg' ? 16 : 14)
</script>

<template>
  <span class="cat-badge" :class="`size-${size}`"
    :style="{ '--c': meta.color, '--cs': meta.soft }">
    <span v-if="withIcon" class="cat-icon">
      <AppIcon :name="meta.icon" :size="iconSize" />
    </span>
    {{ meta.label }}
  </span>
</template>

<style scoped>
.cat-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--cs);
  color: var(--c);
  font-weight: 600;
  border: 1px solid color-mix(in srgb, var(--c) 28%, transparent);
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.size-sm { font-size: var(--text-xs); padding: var(--space-3); }
.size-md { font-size: var(--text-sm); padding: var(--space-3) 12px; }
.size-lg { font-size: var(--text-base); padding: var(--space-3) 16px; }
.cat-icon { display: flex; align-items: center; line-height: 1; }
</style>