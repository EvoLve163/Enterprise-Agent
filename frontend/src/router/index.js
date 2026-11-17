import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '@/layout/index.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/chat',
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/Chat/index.vue'),
        meta: { title: '智能问答', icon: 'ChatDotRound' },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/Knowledge/index.vue'),
        meta: { title: '知识库管理', icon: 'Collection' },
      },
      {
        path: 'agent-monitor',
        name: 'AgentMonitor',
        component: () => import('@/views/AgentMonitor/index.vue'),
        meta: { title: 'Agent 执行监控', icon: 'Monitor' },
      },
      {
        path: 'evaluation',
        name: 'Evaluation',
        component: () => import('@/views/Evaluation/index.vue'),
        meta: { title: '评测管理', icon: 'DataAnalysis' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
