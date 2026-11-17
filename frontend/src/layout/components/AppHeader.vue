<template>
  <div class="app-header">
    <div class="app-header__title">
      {{ route.meta.title || '' }}
    </div>

    <div class="app-header__right">
      <span
        class="health"
        :class="{
          'health--ok': healthState === 'ok',
          'health--bad': healthState === 'bad',
        }"
      >
        <span class="health__dot"></span>
        {{ healthText }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { getHealth } from '@/api/modules/health'

const route = useRoute()

/** 后端健康状态：loading -> ok / bad，每 30s 轮询一次 */
const healthState = ref('loading')

const healthText = computed(() => {
  if (healthState.value === 'ok') return '后端服务正常'
  if (healthState.value === 'bad') return '后端服务不可用'
  return '检测中…'
})

let timer = null

async function checkHealth() {
  try {
    const data = await getHealth()
    healthState.value = data && data.status === 'ok' ? 'ok' : 'bad'
  } catch {
    healthState.value = 'bad'
  }
}

onMounted(() => {
  checkHealth()
  timer = setInterval(checkHealth, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 var(--ea-gap-lg);
}

.app-header__title {
  font-size: 16px;
  font-weight: 600;
}

.health {
  display: inline-flex;
  align-items: center;
  gap: var(--ea-gap-sm);
  font-size: 13px;
  color: var(--ea-text-secondary);
}

.health__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ea-text-muted);
}

.health--ok .health__dot {
  background: var(--ea-success);
}

.health--bad {
  color: var(--ea-danger);
}

.health--bad .health__dot {
  background: var(--ea-danger);
}
</style>
