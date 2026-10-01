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

router.beforeEach((to, from, next) => {
  const isLogin = localStorage.getItem('isLogin') === 'true'
  if (!to.meta.public && !isLogin) {
    next('/login')
  } else if (to.path === '/login' && isLogin) {
    next('/')
  } else {
    next()
  }
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - 智农慧眼`
})

export default router