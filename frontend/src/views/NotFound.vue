<script setup>
import { useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'

const router = useRouter()
</script>

<template>
  <div class="not-found">
    <div class="nf-orb a"></div>
    <div class="nf-orb b"></div>
    <div class="nf-content">
      <div class="nf-icon"><AppIcon name="close" :size="56" /></div>
      <h1 class="nf-code">404</h1>
      <p class="nf-text">页面不存在</p>
      <p class="nf-hint">您访问的页面可能已被移除或地址有误</p>
      <button class="nf-btn" @click="router.push('/')">
        <AppIcon name="home" :size="16" /> 返回首页
      </button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: var(--bg); padding: var(--space-3); position: relative; overflow: hidden;
}
.not-found::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(50% 50% at 25% 30%, rgba(31,185,107,0.18), transparent 60%),
    radial-gradient(50% 50% at 78% 72%, rgba(56,189,248,0.16), transparent 60%);
}
.nf-orb { position: absolute; border-radius: 50%; filter: blur(64px); pointer-events: none; }
.nf-orb.a { width: 360px; height: 360px; background: radial-gradient(circle, var(--accent), transparent 70%); top: -110px; left: -80px; opacity: 0.42; }
.nf-orb.b { width: 300px; height: 300px; background: radial-gradient(circle, var(--tech), transparent 70%); bottom: -100px; right: -60px; opacity: 0.4; }
.nf-content { text-align: center; max-width: 360px; position: relative; z-index: 1; }
.nf-icon {
  width: 88px; height: 88px; margin: 0 auto var(--space-4);
  border-radius: 50%; background: var(--accent-soft); color: var(--accent);
  display: flex; align-items: center; justify-content: center;
  box-shadow: var(--shadow-accent);
}
.nf-code {
  font-family: var(--font-display); font-size: var(--text-5xl);
  font-weight: var(--weight-extrabold); color: var(--accent);
  letter-spacing: -0.04em; line-height: 1; margin-bottom: var(--space-2);
}
.nf-text { font-size: var(--text-xl); font-weight: 600; color: var(--fg); margin-bottom: var(--space-1); }
.nf-hint { font-size: var(--text-sm); color: var(--fg-muted); margin-bottom: var(--space-5); }
.nf-btn {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-5); border-radius: var(--radius-md);
  background: var(--accent-gradient); color: var(--fg-on-accent);
  font-size: var(--text-sm); font-weight: 600; border: none; cursor: pointer;
  transition: all 0.2s var(--ease-out); box-shadow: var(--shadow-accent);
}
.nf-btn:hover { transform: translateY(-1px); box-shadow: var(--shadow-accent-lg); }
</style>