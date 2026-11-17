import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './assets/styles/index.css'

const app = createApp(App)

// 全局注册 Element Plus 图标组件（模板中可直接 <ChatDotRound /> 等）
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
