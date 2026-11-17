<template>
  <div class="app-shell">
    <aside class="app-aside">
      <AppSidebar />
    </aside>
    <div class="app-body">
      <header class="app-header">
        <AppHeader />
      </header>
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import AppSidebar from '@/layout/components/AppSidebar.vue'
import AppHeader from '@/layout/components/AppHeader.vue'
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100%;
}

.app-aside {
  width: var(--ea-sidebar-width);
  flex-shrink: 0;
  background: var(--ea-surface);
  border-right: 1px solid var(--ea-border);
}

.app-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: var(--ea-header-height);
  flex-shrink: 0;
  background: var(--ea-surface);
  border-bottom: 1px solid var(--ea-border);
}

.app-main {
  flex: 1;
  min-height: 0;
  padding: var(--ea-gap-lg);
  overflow-y: auto;
}
</style>
