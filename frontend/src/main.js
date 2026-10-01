import { createApp } from 'vue'
import { createPinia } from 'pinia'
// PERF-001：**不要** app.use(ElementPlus) —— 那会把整套组件全量注册，
// vite.config.js 里配置的 ElementPlusResolver（按需引入）会被完全架空
// （element-plus chunk 曾达 302KB gzip）。组件由插件按模板实际使用自动导入，
// 中文语言包改由 App.vue 的 <el-config-provider> 提供。
import 'element-plus/dist/index.css'
// PERF-001：不再全量注册 @element-plus/icons-vue（会把整套图标打进首屏包）。
// 各组件已按需 import 自己用到的图标，此处无需注册。

import App from './App.vue'
import router from './router'
import './styles/variables.css'
import './styles/global.css'

const app = createApp(App)

// 滚动揭示指令：进入视口时添加 .in 触发编排入场
app.directive('reveal', {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (binding.value) el.setAttribute('data-delay', String(binding.value))
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.classList.add('in')
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            el.classList.add('in')
            io.unobserve(el)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    )
    io.observe(el)
    el._revealObserver = io
  },
  unmounted(el) {
    if (el._revealObserver) el._revealObserver.disconnect()
  },
})

const pinia = createPinia()
app.use(pinia)
app.use(router)

// 刷新后先用本地 token 换回身份；token 已失效则清空，由路由守卫送回登录页
import { useUserStore } from './stores/user'
import api from './api'
const userStore = useUserStore(pinia)
userStore.restore().then((ok) => {
  if (ok) { userStore.loadStats(); api.systemInfo().then(d => (userStore.systemInfo = d)).catch(() => {}) }
}).catch(() => {})

app.mount('#app')