<script setup>
const props = defineProps({
  shape: { type: String, default: 'rect' },
  width: { type: String, default: '100%' },
  height: { type: String, default: '16px' },
  radius: { type: String, default: 'var(--radius-sm)' },
  count: { type: Number, default: 1 },
  gap: { type: String, default: 'var(--space-2)' },
  animated: { type: Boolean, default: true },
})
</script>

<template>
  <div class="skeleton-group" :style="{ gap }">
    <div
      v-for="i in count"
      :key="i"
      class="skeleton"
      :class="[`skeleton--${shape}`, { 'is-animated': animated }]"
      :style="{ width, height, borderRadius: shape === 'circle' ? '50%' : radius }"
    ></div>
  </div>
</template>

<style scoped>
.skeleton-group { display: flex; flex-direction: column; }
.skeleton {
  background: var(--bg-muted);
  flex-shrink: 0;
}
.skeleton--text { border-radius: var(--radius-xs); }
.skeleton--circle { border-radius: 50%; }
.is-animated {
  background: linear-gradient(
    90deg,
    var(--bg-muted) 25%,
    var(--bg-hover) 50%,
    var(--bg-muted) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite linear;
}
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>