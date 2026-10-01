import { createRouter, createWebHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/',
    component: DefaultLayout,
    children: [
      { path: '', name: 'home', component: () => import('@/views/Home.vue'), meta: { title: '首页' } },
      { path: 'recognize', name: 'recognize', component: () => import('@/views/Recognize.vue'), meta: { title: '智能识别' } },
      { path: 'advisor', name: 'advisor', component: () => import('@/views/Advisor.vue'), meta: { title: 'AI 农事顾问' } },
      { path: 'history', name: 'history', component: () => import('@/views/History.vue'), meta: { title: '诊断记录' } },
      { path: 'calendar', name: 'calendar', component: () => import('@/views/Calendar.vue'), meta: { title: '农事日历' } },

    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在', public: true },
  },
]

const router = createRouter({ history: createWebHistory(), routes })

// 守卫依据：后端签发的 JWT 是否存在（SEC-001）。
// 令牌是否存在只决定“能否进内页”；令牌是否有效由 axios 401 拦截 + 启动时 /api/auth/me 校验兜底。
function hasToken() {
  return !!localStorage.getItem('agrieye_token')
}

router.beforeEach((to, from, next) => {
  const logged = hasToken()
  if (!to.meta.public && !logged) {
    next({ path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : undefined })
  } else if (to.path === '/login' && logged) {
    next('/')
  } else {
    next()
  }
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - 智农慧眼`
})

export default router