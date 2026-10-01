<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const isLogin = ref(true)
const loading = ref(false)

const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
})

/** 演示一键登录：直接以内置的 admin 账号走真实认证链路 */
async function demoLogin() {
  form.value.username = 'admin'
  form.value.password = '123456'
  loading.value = true
  try {
    await userStore.login('admin', '123456')
    ElMessage.success('已进入演示模式')
    router.push(route.query.redirect || '/')
  } catch {
    /* 错误提示由 axios 拦截器统一弹出 */
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  if (!isLogin.value && form.value.password !== form.value.confirmPassword) {
    ElMessage.warning('两次密码输入不一致')
    return
  }
  loading.value = true
  try {
    if (isLogin.value) {
      await userStore.login(form.value.username, form.value.password)
      ElMessage.success('登录成功')
    } else {
      await userStore.register({
        username: form.value.username,
        password: form.value.password,
      })
      ElMessage.success('注册成功，已自动登录')
    }
    router.push(route.query.redirect || '/')
  } catch {
    /* 错误提示由 axios 拦截器统一弹出 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-circle c1"></div>
      <div class="bg-circle c2"></div>
      <div class="bg-circle c3"></div>
    </div>

    <div class="login-card">
      <div class="card-left">
        <div class="brand">
          <div class="brand-mark"><AppIcon name="leafShield" :size="32" /></div>
          <strong class="brand-name">智农慧眼</strong>
          <span class="brand-sub">AgriEye · AI 农技助手</span>
        </div>
        <div class="features">
          <div class="feature-item">
            <AppIcon name="scanSearch" :size="20" />
            <span>多模态病虫害智能识别</span>
          </div>
          <div class="feature-item">
            <AppIcon name="messagesSquare" :size="20" />
            <span>AI 农事顾问即时问答</span>
          </div>
          <div class="feature-item">
            <AppIcon name="folderClock" :size="20" />
            <span>诊断档案全程可追溯</span>
          </div>
          <div class="feature-item">
            <AppIcon name="calendarRange" :size="20" />
            <span>农事日历智能提醒</span>
          </div>
        </div>
      </div>

      <div class="card-right">
        <div class="form-header">
          <h2>{{ isLogin ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ isLogin ? '登录以继续使用' : '注册新账号开始体验' }}</p>
        </div>

        <div class="mode-tabs">
          <button :class="['tab', { active: isLogin }]" @click="isLogin = true">登录</button>
          <button :class="['tab', { active: !isLogin }]" @click="isLogin = false">注册</button>
        </div>

        <form class="login-form" @submit.prevent="handleSubmit">
          <div class="field">
            <label>账号</label>
            <div class="input-wrap">
              <AppIcon name="user" :size="16" />
              <input v-model="form.username" type="text" placeholder="请输入账号" />
            </div>
          </div>
          <div class="field">
            <label>密码</label>
            <div class="input-wrap">
              <AppIcon name="shield" :size="16" />
              <input v-model="form.password" type="password" placeholder="请输入密码" />
            </div>
          </div>
          <div class="field" v-if="!isLogin">
            <label>确认密码</label>
            <div class="input-wrap">
              <AppIcon name="shield" :size="16" />
              <input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" />
            </div>
          </div>
          <button type="submit" class="submit-btn" :disabled="loading">
            <AppIcon name="check" :size="16" v-if="!loading" />
            <span>{{ loading ? '处理中…' : (isLogin ? '登 录' : '注 册') }}</span>
          </button>
        </form>

        <button
          v-if="isLogin"
          type="button"
          class="demo-btn"
          :disabled="loading"
          @click="demoLogin"
        >
          <AppIcon name="sparkles" :size="16" />
          <span>演示一键进入（admin / 123456）</span>
        </button>

        <div class="form-footer" v-if="isLogin">
          <span>默认账号由服务端初始化，口令以加盐哈希存储</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: var(--bg); position: relative; overflow: hidden;
}

.login-bg { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.login-bg::before {
  content: ''; position: absolute; inset: 0;
  background:
    radial-gradient(60% 50% at 12% 18%, rgba(31,185,107,0.20), transparent 60%),
    radial-gradient(50% 50% at 88% 82%, rgba(56,189,248,0.18), transparent 60%),
    radial-gradient(42% 42% at 72% 12%, rgba(190,242,100,0.12), transparent 60%);
}
.bg-circle { position: absolute; border-radius: 50%; filter: blur(48px); }
.c1 { width: 440px; height: 440px; background: radial-gradient(circle, var(--accent), transparent 70%); top: -130px; left: -110px; opacity: 0.55; }
.c2 { width: 380px; height: 380px; background: radial-gradient(circle, var(--tech), transparent 70%); bottom: -130px; right: -90px; opacity: 0.5; }
.c3 { width: 300px; height: 300px; background: radial-gradient(circle, var(--lime), transparent 70%); top: 44%; right: 24%; opacity: 0.32; }
:global([data-theme='light']) .login-bg::before { opacity: 0.7; }
:global([data-theme='light']) .bg-circle { opacity: 0.4; }

.login-card {
  display: flex; width: 800px; max-width: 90vw; min-height: 480px;
  background: var(--bg-elevated); border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-2xl); border: 1px solid var(--border);
  z-index: 1; overflow: hidden;
}
@media (max-width: 768px) { .login-card { flex-direction: column; width: 90vw; } }

.card-left {
  flex: 1; padding: var(--space-3); display: flex; flex-direction: column;
  justify-content: center; gap: var(--space-5);
  background: var(--bg-muted); border-right: 1px solid var(--border);
}
@media (max-width: 768px) { .card-left { display: none; } }

.brand { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-1); }
.brand-mark {
  width: 48px; height: 48px; border-radius: var(--radius-md);
  background: var(--accent); color: var(--fg-on-accent);
  display: flex; align-items: center; justify-content: center; margin-bottom: var(--space-2);
  box-shadow: var(--shadow-accent);
}
.brand-name { font-family: var(--font-display); font-size: var(--text-2xl); font-weight: var(--weight-extrabold); color: var(--accent); }
.brand-sub { font-size: var(--text-sm); color: var(--fg-muted); }

.features { display: flex; flex-direction: column; gap: var(--space-3); }
.feature-item { display: flex; align-items: center; gap: var(--space-2); color: var(--fg-secondary); font-size: var(--text-sm); }
.feature-item svg { color: var(--accent); }

.card-right {
  flex: 1; padding: var(--space-3); display: flex; flex-direction: column; justify-content: center; gap: var(--space-4);
}

.form-header h2 { font-family: var(--font-display); font-size: var(--text-xl); font-weight: var(--weight-bold); color: var(--fg); }
.form-header p { font-size: var(--text-sm); color: var(--fg-muted); margin-top: var(--space-1); }

.mode-tabs { display: flex; gap: var(--space-1); padding: 3px; background: var(--bg-muted); border-radius: var(--radius-md); }
.tab { flex: 1; padding: var(--space-2); border: none; background: transparent; color: var(--fg-muted); font-size: var(--text-sm); font-weight: 600; border-radius: var(--radius-sm); cursor: pointer; transition: all var(--duration) var(--ease-out); }
.tab.active { background: var(--bg-elevated); color: var(--accent); box-shadow: var(--shadow-sm); }

.login-form { display: flex; flex-direction: column; gap: var(--space-3); }
.field { display: flex; flex-direction: column; gap: var(--space-1); }
.field label { font-size: var(--text-xs); font-weight: 600; color: var(--fg-secondary); }
.input-wrap { display: flex; align-items: center; gap: var(--space-2); padding: 0 var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--bg-elevated); transition: var(--transition); }
.input-wrap svg { color: var(--fg-subtle); flex-shrink: 0; }
.input-wrap:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.input-wrap input { flex: 1; border: none; outline: none; background: none; padding: var(--space-2) 0; font-size: var(--text-sm); color: var(--fg); font-family: var(--font-ui); }
.input-wrap input::placeholder { color: var(--fg-subtle); }

.submit-btn { display: flex; align-items: center; justify-content: center; gap: var(--space-2); padding: var(--space-3); margin-top: var(--space-2); border: none; border-radius: var(--radius-md); background: var(--accent); color: var(--fg-on-accent); font-size: var(--text-md); font-weight: var(--weight-semibold); cursor: pointer; transition: all var(--duration) var(--ease-out); box-shadow: var(--shadow-accent); }
.submit-btn:hover { background: var(--accent-hover); transform: translateY(-1px); }
.submit-btn:active { transform: translateY(0); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 演示一键进入：次级按钮，弱于主按钮但清晰可点 */
.demo-btn {
  display: flex; align-items: center; justify-content: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px dashed var(--border-strong); border-radius: var(--radius-md);
  background: transparent; color: var(--fg-secondary);
  font-size: var(--text-sm); font-weight: 600; cursor: pointer;
  transition: all var(--duration) var(--ease-out);
}
.demo-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.demo-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.demo-btn svg { flex-shrink: 0; }

.form-footer { text-align: center; font-size: var(--text-xs); color: var(--fg-subtle); padding-top: var(--space-2); border-top: 1px solid var(--border); }
</style>