<template>
  <div class="sidebar">
    <!-- 品牌区 -->
    <div class="sidebar__brand">
      <div class="sidebar__logo">
        <el-icon :size="20"><Cpu /></el-icon>
      </div>
      <div class="sidebar__brand-text">
        <span class="sidebar__name">Enterprise Agent</span>
        <span class="sidebar__sub">企业级 AI 工作台</span>
      </div>
    </div>

    <!-- 导航菜单（router 模式：点击跳转对应路由） -->
    <el-menu
      class="sidebar__menu"
      :default-active="route.path"
      router
    >
      <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.title }}</span>
      </el-menu-item>
    </el-menu>

    <!-- 底部版本信息 -->
    <div class="sidebar__footer">v0.1.0 · 第二阶段骨架</div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const menus = [
  { path: '/chat', title: '智能问答', icon: 'ChatDotRound' },
  { path: '/knowledge', title: '知识库管理', icon: 'Collection' },
  { path: '/agent-monitor', title: 'Agent 执行监控', icon: 'Monitor' },
  { path: '/evaluation', title: '评测管理', icon: 'DataAnalysis' },
]
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--ea-gap-sm);
  height: var(--ea-header-height);
  padding: 0 var(--ea-gap-md);
  border-bottom: 1px solid var(--ea-border);
}

.sidebar__logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--ea-primary);
  color: #fff;
  flex-shrink: 0;
}

.sidebar__brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  min-width: 0;
}

.sidebar__name {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar__sub {
  font-size: 12px;
  color: var(--ea-text-muted);
  white-space: nowrap;
}

.sidebar__menu {
  flex: 1;
  border-right: none;
  padding: var(--ea-gap-sm);
}

.sidebar__menu .el-menu-item {
  border-radius: var(--ea-radius);
  margin-bottom: 2px;
}

.sidebar__footer {
  padding: var(--ea-gap-md);
  font-size: 12px;
  color: var(--ea-text-muted);
  border-top: 1px solid var(--ea-border);
}
</style>
