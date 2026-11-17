# Enterprise Agent 前端

Vue 3 + Vite + Element Plus 企业级 AI 工作台。

## 技术栈

- Vue 3（Composition API）+ Vite 7
- Element Plus + @element-plus/icons-vue（企业级组件库，中文 locale）
- Vue Router 4（四个业务页面路由）
- Axios（统一封装：环境变量 baseURL、超时、错误归一化）

## 快速开始

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

构建：

```bash
npm run build      # 产物输出至 dist/
npm run preview    # 本地预览构建产物
```

## 环境变量

| 变量 | 说明 | 示例 |
|---|---|---|
| `VITE_API_BASE_URL` | 后端 FastAPI 地址 | `http://127.0.0.1:8000` |

开发环境读取 `.env.development`，生产构建读取 `.env.production`。

## 目录结构

```
frontend/src/
├── api/            # Axios 封装与接口模块（request.js + modules/）
├── assets/         # 全局样式（设计基线 CSS 变量）
├── components/     # 通用组件（PagePlaceholder）
├── layout/         # 工作台外壳（侧边栏 + 顶栏 + 主区域）
├── router/         # 路由定义
├── utils/          # 格式化工具（字节/时间/时长）
├── views/          # 页面：Chat / Knowledge / AgentMonitor / Evaluation
├── App.vue
└── main.js
```
