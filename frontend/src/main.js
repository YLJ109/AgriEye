import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

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

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 刷新后先用本地 token 换回身份；token 已失效则清空，由路由守卫送回登录页
import { useUserStore } from './stores/user'
import api from './api'
const userStore = useUserStore(pinia)
userStore.restore().then((ok) => {
  if (ok) { userStore.loadStats(); api.systemInfo().then(d => (userStore.systemInfo = d)).catch(() => {}) }
}).catch(() => {})

app.mount('#app')