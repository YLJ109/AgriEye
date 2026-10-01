<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import { Sprout, ChevronDown, LogOut, User } from 'lucide-vue-next'
import AppIcon from '@/components/AppIcon.vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)
const theme = ref(localStorage.getItem('theme') || 'dark')
const isMobile = ref(false)
const mobileSidebarOpen = ref(false)
const showLogoutConfirm = ref(false)
const username = localStorage.getItem('username') || '管理员'

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '首页')

const menus = [
  { path: '/', label: '工作台', icon: 'dashboard', desc: '总览与诊断入口' },
  { path: '/recognize', label: '智能识别', icon: 'scanSearch', badge: 'AI', desc: '多模态病虫害识别' },
  { path: '/advisor', label: '农事顾问', icon: 'messagesSquare', desc: 'AI 问答与方案' },
  { path: '/history', label: '诊断档案', icon: 'folderClock', desc: '历史记录追溯' },
  { path: '/calendar', label: '农事日历', icon: 'calendarRange', desc: '节气与提醒' },
]

const userMenuOpen = ref(false)

function toggleCollapse() {
  if (isMobile.value) mobileSidebarOpen.value = !mobileSidebarOpen.value
  else collapsed.value = !collapsed.value
}
function closeMobileSidebar() { mobileSidebarOpen.value = false }
function closePopovers() { userMenuOpen.value = false }
function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
  localStorage.setItem('theme', theme.value)
}
function handleLogout() { showLogoutConfirm.value = true; closePopovers() }
function confirmLogout() {
  showLogoutConfirm.value = false
  localStorage.removeItem('isLogin')
  localStorage.removeItem('username')
  ElMessage.success('已退出登录')
  router.push('/login')
}

function checkScreen() {
  isMobile.value = window.innerWidth <= 900
  if (isMobile.value) { collapsed.value = true; mobileSidebarOpen.value = false }
}
function onDocClick() { closePopovers() }

onMounted(() => {
  document.documentElement.setAttribute('data-theme', theme.value)
  userStore.loadSystemInfo(); userStore.loadStats()
  checkScreen()
  window.addEventListener('resize', checkScreen)
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', checkScreen)
  document.removeEventListener('click', onDocClick)
})
watch(() => route.path, () => { closeMobileSidebar(); closePopovers() })
</script>

<template>
  <div class="layout" :class="{ collapsed, 'mobile-open': mobileSidebarOpen }">
    <div class="sidebar-overlay" v-if="mobileSidebarOpen" @click="closeMobileSidebar"></div>

    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="brand" :class="{ collapsed }">
        <div class="brand-mark">
          <Sprout :size="24" />
        </div>
        <div class="brand-text" v-show="!collapsed">
          <strong>智农慧眼</strong>
          <span>AgriEye · AI 农技助手</span>
        </div>
      </div>

      <nav class="nav">
        <RouterLink v-for="m in menus" :key="m.path" :to="m.path"
          class="nav-item" :class="{ active: activeMenu === m.path }">
          <span class="nav-icon-wrap">
            <AppIcon :name="m.icon" :size="20" />
          </span>
          <span class="nav-body" v-show="!collapsed">
            <span class="nav-label">{{ m.label }}</span>
            <span class="nav-desc">{{ m.desc }}</span>
          </span>
          <span class="nav-badge" v-show="!collapsed && m.badge">{{ m.badge }}</span>
          <span class="nav-active-bar"></span>
        </RouterLink>
      </nav>

      <div class="sidebar-bottom">
        <div class="user-card" :class="{ collapsed }" v-show="!collapsed" @click.stop="userMenuOpen = !userMenuOpen">
          <div class="user-avatar">{{ username.slice(0, 1).toUpperCase() }}</div>
          <div class="user-info">
            <strong class="user-name">{{ username }}</strong>
            <span class="user-role"><span class="dot"></span>在线</span>
          </div>
          <ChevronDown :size="14" class="user-chev" :class="{ open: userMenuOpen }" />
        </div>
        <div class="user-avatar-collapsed" v-show="collapsed" @click.stop="userMenuOpen = !userMenuOpen">
          {{ username.slice(0, 1).toUpperCase() }}
        </div>
        <transition name="pop">
          <div class="user-menu" v-if="userMenuOpen && !collapsed" @click.stop>
            <div class="um-item" @click="router.push('/')"><User :size="15" /> 个人中心</div>
            <div class="um-item danger" @click="handleLogout"><LogOut :size="15" /> 退出登录</div>
          </div>
        </transition>
        <div class="offline-tag" v-show="!collapsed">
          <span class="dot"></span>
          <span>离线模式可用</span>
          <span class="version">v2.0</span>
        </div>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-wrap">
      <header class="topbar">
        <div class="topbar-left">
          <button class="collapse-btn" @click.stop="toggleCollapse">
            <AppIcon :name="collapsed ? 'panelOpen' : 'panelClose'" :size="20" />
          </button>
          <div class="breadcrumb">
            <span class="crumb-root">智农慧眼</span>
            <AppIcon name="arrowRight" :size="14" class="crumb-sep" />
            <span class="crumb-current">{{ currentTitle }}</span>
          </div>
        </div>
        <div class="topbar-right">
          <button class="icon-btn" @click.stop="toggleTheme" title="切换主题">
            <AppIcon :name="theme === 'light' ? 'moonOutline' : 'sunOutline'" :size="20" />
          </button>
        </div>
      </header>

      <main class="content">
        <ErrorBoundary>
          <!-- KeepAlive：切换路由不卸载组件，保留各页已加载的内容与状态 -->
          <RouterView v-slot="{ Component }">
            <KeepAlive>
              <component :is="Component" />
            </KeepAlive>
          </RouterView>
        </ErrorBoundary>
      </main>
    </div>

    <transition name="fade">
      <div class="logout-overlay" v-if="showLogoutConfirm" @click.self="showLogoutConfirm = false">
        <div class="logout-dialog">
          <div class="logout-icon"><LogOut :size="28" /></div>
          <h3>确认退出登录？</h3>
          <p>退出后将返回登录页面</p>
          <div class="logout-actions">
            <button class="btn-cancel" @click="showLogoutConfirm = false">取消</button>
            <button class="btn-confirm" @click="confirmLogout">确认退出</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; background: transparent; position: relative; z-index: 1; }

/* ===== 侧边栏 ===== */
.sidebar {
  width: var(--sidebar-width);
  background: color-mix(in srgb, var(--bg-elevated) 82%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  transition: width 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  position: sticky; top: 0; height: 100vh; z-index: var(--z-sticky);
}
.layout.collapsed .sidebar { width: var(--sidebar-collapsed); }

.brand {
  display: flex; align-items: center; gap: var(--space-3);
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--border);
  height: var(--topbar-height);
  flex-shrink: 0;
}
.brand-mark {
  width: 40px; height: 40px; border-radius: var(--radius-md);
  background: var(--accent-gradient); display: flex; align-items: center; justify-content: center;
  color: var(--fg-on-accent); flex-shrink: 0; box-shadow: var(--shadow-accent);
  transition: transform 0.3s var(--ease-out);
}
.brand-mark:hover { transform: scale(1.06) rotate(-4deg); }
.brand-text { display: flex; flex-direction: column; line-height: 1.3; white-space: nowrap; }
.brand-text strong {
  font-family: var(--font-display); font-size: var(--text-lg);
  font-weight: var(--weight-extrabold); letter-spacing: -0.02em;
  color: var(--fg);
}
.brand-text span { font-size: var(--text-xs); color: var(--fg-muted); letter-spacing: 0.02em; }

.nav { flex: 1; padding: var(--space-4) var(--space-3); display: flex; flex-direction: column; gap: var(--space-1); overflow-y: auto; }
.nav-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  color: var(--fg-secondary); font-size: var(--text-base); font-weight: 500;
  position: relative; transition: background 0.2s var(--ease-out), color 0.2s var(--ease-out);
  text-decoration: none; overflow: hidden;
}
.nav-item:hover { background: var(--bg-muted); color: var(--fg); }
.nav-item.active { background: var(--accent-soft); color: var(--accent); }
.nav-icon-wrap { display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; flex-shrink: 0; transition: color 0.2s var(--ease-out); z-index: 1; }
.nav-body { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; z-index: 1; }
.nav-label { font-weight: 600; white-space: nowrap; }
.nav-desc { font-size: 11px; color: var(--fg-subtle); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nav-item.active .nav-desc { color: color-mix(in srgb, var(--accent) 70%, var(--fg-subtle)); }
.nav-badge {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: var(--radius-full);
  background: var(--lime); color: #1a2a05; letter-spacing: 0.5px; margin-left: auto; z-index: 1;
}
.nav-active-bar {
  position: absolute; left: 0; top: 50%; transform: translateY(-50%) scaleY(0);
  width: 3px; height: 56%; border-radius: var(--radius-full);
  background: var(--accent-gradient); opacity: 0; transition: all 0.24s var(--ease-out); z-index: 0;
}
.nav-item.active .nav-active-bar { opacity: 1; transform: translateY(-50%) scaleY(1); }

/* ===== 侧栏底部 ===== */
.sidebar-bottom {
  border-top: 1px solid var(--border);
  padding: var(--space-3);
  flex-shrink: 0;
  display: flex; flex-direction: column; gap: var(--space-2);
  position: relative;
}
.user-card {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--bg-muted);
  transition: var(--transition); cursor: pointer;
}
.user-card:hover { background: var(--bg-hover); }
.user-avatar, .user-avatar-collapsed {
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--accent-gradient); color: var(--fg-on-accent);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-display); font-weight: var(--weight-extrabold); font-size: var(--text-md);
  flex-shrink: 0;
}
.user-avatar-collapsed { margin: 0 auto; cursor: pointer; }
.user-info { flex: 1; min-width: 0; display: flex; flex-direction: column; line-height: 1.3; }
.user-name { font-size: var(--text-sm); font-weight: 600; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { font-size: var(--text-xs); color: var(--fg-muted); display: flex; align-items: center; gap: 5px; }
.user-role .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--success); animation: pulse-soft 2s infinite; }
.user-chev { color: var(--fg-subtle); transition: transform 0.2s var(--ease-out); }
.user-chev.open { transform: rotate(180deg); }

.user-menu {
  position: absolute; bottom: calc(100% - 8px); left: var(--space-3); right: var(--space-3);
  background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg); padding: var(--space-2); z-index: 5;
}
.um-item { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm); font-size: var(--text-sm); color: var(--fg-secondary); cursor: pointer; transition: var(--transition); white-space: nowrap; }
.um-item svg { flex-shrink: 0; }
.um-item:hover { background: var(--bg-muted); color: var(--fg); }
.um-item.danger { color: var(--danger); }
.um-item.danger:hover { background: color-mix(in srgb, var(--danger) 12%, transparent); }

.offline-tag {
  display: flex; align-items: center; gap: 6px;
  font-size: var(--text-xs); color: var(--fg-muted);
  padding: 0 var(--space-2);
}
.offline-tag .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--success); animation: pulse-soft 2s infinite; flex-shrink: 0; }
.offline-tag .version { margin-left: auto; color: var(--fg-subtle); font-family: var(--font-mono); }

/* ===== 主区域 ===== */
.main-wrap { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.topbar {
  height: var(--topbar-height); background: color-mix(in srgb, var(--bg-elevated) 80%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--space-6); position: sticky; top: 0; z-index: var(--z-sticky);
}
.topbar-left { display: flex; align-items: center; gap: var(--space-4); }
.collapse-btn {
  width: 38px; height: 38px; border-radius: var(--radius-md);
  border: none; background: transparent; color: var(--fg-secondary);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: var(--transition);
}
.collapse-btn:hover { background: var(--bg-muted); color: var(--fg); }
.breadcrumb { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); }
.crumb-root { color: var(--fg-muted); }
.crumb-sep { color: var(--fg-subtle); }
.crumb-current { color: var(--fg); font-weight: 600; }

.topbar-right { display: flex; align-items: center; gap: var(--space-2); }
.icon-btn {
  width: 38px; height: 38px; border-radius: var(--radius-md);
  border: none; background: transparent; color: var(--fg-secondary);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: var(--transition); position: relative;
}
.icon-btn:hover { background: var(--bg-muted); color: var(--fg); }

.content { flex: 1; padding: var(--space-4) var(--space-5) var(--space-6); overflow-y: auto; }
@media (max-width: 900px) { .content { padding: var(--space-3) var(--space-4) var(--space-5); } }

/* ===== 退出登录弹窗 ===== */
.logout-overlay { position: fixed; inset: 0; background: rgba(3,12,8,0.5); z-index: var(--z-modal); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
.logout-dialog {
  background: var(--bg-elevated); border-radius: var(--radius-xl); padding: var(--space-6);
  text-align: center; box-shadow: var(--shadow-2xl); max-width: 360px; width: 90%;
  border: 1px solid var(--border); animation: scaleIn 0.3s var(--ease-out);
}
.logout-icon {
  width: 56px; height: 56px; border-radius: 50%; margin: 0 auto var(--space-4);
  background: color-mix(in srgb, var(--danger) 16%, transparent); color: var(--danger);
  display: flex; align-items: center; justify-content: center;
}
.logout-dialog h3 { font-size: var(--text-lg); margin-bottom: var(--space-2); }
.logout-dialog p { color: var(--fg-muted); font-size: var(--text-sm); margin-bottom: var(--space-5); }
.logout-actions { display: flex; gap: var(--space-3); justify-content: center; }
.btn-cancel, .btn-confirm { padding: var(--space-2) var(--space-5); border-radius: var(--radius-md); font-size: var(--text-sm); font-weight: 600; cursor: pointer; border: none; transition: var(--transition); }
.btn-cancel { background: var(--bg-muted); color: var(--fg-secondary); }
.btn-cancel:hover { background: var(--bg-hover); }
.btn-confirm { background: var(--danger); color: #fff; }
.btn-confirm:hover { filter: brightness(1.08); }

/* ===== 过渡 ===== */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s var(--ease-out); }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.pop-enter-active, .pop-leave-active { transition: opacity 0.18s var(--ease-out), transform 0.18s var(--ease-out); }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(-6px); }

.sidebar-overlay { position: fixed; inset: 0; background: rgba(3,12,8,0.55); z-index: calc(var(--z-overlay) - 1); backdrop-filter: blur(2px); }

@media (max-width: 900px) {
  .sidebar { width: var(--sidebar-collapsed); }
  .layout.mobile-open .sidebar { width: var(--sidebar-width); position: fixed; z-index: var(--z-overlay); box-shadow: var(--shadow-2xl); }
  .content { padding: var(--space-3); }
  .topbar { padding: 0 var(--space-4); }
}
@media (max-width: 480px) {
  .breadcrumb .crumb-root, .breadcrumb .crumb-sep { display: none; }
}
</style>
