<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },      // 0–1
  size: { type: Number, default: 92 },
  stroke: { type: Number, default: 8 },
  label: { type: String, default: '' },
  accent: { type: String, default: 'accent' }, // accent | tech | lime | warning | danger
})

const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const pct = computed(() => Math.round(Math.min(1, Math.max(0, props.value)) * 100))
const offset = computed(() => circumference.value * (1 - Math.min(1, Math.max(0, props.value))))

const palette = {
  accent: 'var(--accent)',
  tech: 'var(--tech)',
  lime: 'var(--lime)',
  warning: 'var(--warning)',
  danger: 'var(--danger)',
}
const color = computed(() => palette[props.accent] || 'var(--accent)')
</script>

<template>
  <div class="conf-ring" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <circle class="cr-bg" :cx="size / 2" :cy="size / 2" :r="radius"
        :stroke-width="stroke" fill="none" />
      <circle class="cr-fg" :cx="size / 2" :cy="size / 2" :r="radius"
        :stroke-width="stroke" fill="none" :stroke="color" stroke-linecap="round"
        :stroke-dasharray="circumference" :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`" />
    </svg>
    <div class="cr-center">
      <span class="cr-pct" :style="{ color }">{{ pct }}<small>%</small></span>
      <span class="cr-label" v-if="label">{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.conf-ring { position: relative; display: grid; place-items: center; }
.cr-bg { stroke: var(--border-strong); opacity: .45; }
.cr-fg { transition: stroke-dashoffset .9s var(--ease-out); }
.cr-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 1px; pointer-events: none;
}
.cr-pct { font-size: 19px; font-weight: 800; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.cr-pct small { font-size: 11px; font-weight: 700; margin-left: 1px; }
.cr-label { font-size: 10px; color: var(--fg-muted); letter-spacing: .02em; }
</style>
