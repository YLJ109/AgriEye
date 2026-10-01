<script setup>
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  label: String,
  value: { type: [Number, String], default: 0 },
  suffix: String,
  icon: String,
  trend: Number,
  accent: { type: String, default: 'accent' },
  spark: { type: Array, default: () => [] },
  loading: Boolean,
})

const accentMap = {
  accent: { c: 'var(--accent)', cs: 'var(--accent-soft)', g: 'var(--accent-gradient)' },
  tech: { c: 'var(--tech)', cs: 'var(--tech-soft)', g: 'var(--tech-gradient)' },
  lime: { c: 'var(--lime)', cs: 'var(--lime-soft)', g: 'var(--lime-gradient)' },
}
const ac = computed(() => accentMap[props.accent] || accentMap.accent)

const displayValue = computed(() => {
  if (props.loading) return '—'
  const v = props.value
  return typeof v === 'number' ? v.toLocaleString() : v
})

const sparkPath = computed(() => {
  const s = props.spark
  if (!s || s.length < 2) return ''
  const w = 100, h = 32, max = Math.max(...s), min = Math.min(...s)
  const span = max - min || 1
  return s.map((v, i) => {
    const x = (i / (s.length - 1)) * w
    const y = h - ((v - min) / span) * (h - 4) - 2
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})
</script>

<template>
  <div class="stat-card" :style="{ '--c': ac.c, '--cs': ac.cs, '--g': ac.g }">
    <div class="stat-top">
      <div class="stat-icon" v-if="icon">
        <AppIcon :name="icon" :size="18" />
      </div>
      <span class="stat-label">{{ label }}</span>
    </div>
    <div class="stat-value" :class="{ loading }">
      <span v-if="!loading">{{ displayValue }}</span>
      <span v-else class="shimmer-val"></span>
      <span class="stat-suffix" v-if="suffix">{{ suffix }}</span>
    </div>
    <div class="stat-foot">
      <div class="stat-trend" v-if="trend !== undefined">
        <span :class="trend >= 0 ? 'up' : 'down'">
          <AppIcon :name="trend >= 0 ? 'trendUp' : 'trendDown'" :size="12" /> {{ Math.abs(trend) }}%
        </span>
        <span class="trend-label">较上周</span>
      </div>
      <svg v-if="sparkPath" class="spark" viewBox="0 0 100 32" preserveAspectRatio="none">
        <path :d="sparkPath" fill="none" stroke="var(--c)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-4) var(--space-3);
  position: relative;
  overflow: hidden;
  transition: transform var(--duration) var(--ease-out), box-shadow var(--duration) var(--ease-out), border-color var(--duration) var(--ease-out);
}
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--g); opacity: 0.9;
}
.stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-3px); border-color: color-mix(in srgb, var(--c) 40%, var(--border)); }

.stat-top { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
.stat-icon {
  width: 34px; height: 34px; border-radius: var(--radius-md);
  background: var(--cs); display: flex; align-items: center; justify-content: center;
  color: var(--c);
}
.stat-label { color: var(--fg-muted); font-size: var(--text-sm); font-weight: 500; }

.stat-value {
  font-family: var(--font-display);
  font-size: var(--text-3xl);
  font-weight: var(--weight-extrabold);
  color: var(--fg);
  letter-spacing: -0.03em;
  display: flex; align-items: baseline; gap: var(--space-2);
  line-height: 1;
}
.stat-suffix { font-size: var(--text-base); color: var(--fg-muted); font-weight: 500; }
.shimmer-val { display: inline-block; width: 64px; height: 30px; border-radius: var(--radius-sm); background: linear-gradient(90deg, var(--bg-muted) 25%, var(--bg-hover) 50%, var(--bg-muted) 75%); background-size: 200% 100%; animation: stat-shimmer 1.5s infinite linear; }
@keyframes stat-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.stat-foot { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-2); margin-top: var(--space-3); }
.stat-trend { display: flex; align-items: center; gap: var(--space-1); font-size: var(--text-xs); }
.stat-trend .up { color: var(--success); font-weight: 700; display: inline-flex; align-items: center; gap: 2px; }
.stat-trend .down { color: var(--danger); font-weight: 700; display: inline-flex; align-items: center; gap: 2px; }
.trend-label { color: var(--fg-subtle); }
.spark { width: 96px; height: 30px; opacity: 0.9; }
</style>
