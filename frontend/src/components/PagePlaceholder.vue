<template>
  <div class="page-placeholder">
    <el-icon class="page-placeholder__icon" :size="64">
      <component :is="icon" />
    </el-icon>
    <h3 class="page-placeholder__title">{{ title }}</h3>
    <p class="page-placeholder__desc">{{ description }}</p>
    <p v-if="hint" class="page-placeholder__hint">{{ hint }}</p>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: 'Box' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  hint: { type: String, default: '' },
})
</script>

<style scoped>
.page-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 72px 24px;
  text-align: center;
}

.page-placeholder__icon {
  color: var(--ea-primary);
  opacity: 0.85;
}

.page-placeholder__title {
  margin: var(--ea-gap-md) 0 var(--ea-gap-xs);
  font-size: 16px;
  font-weight: 600;
}

.page-placeholder__desc {
  margin: 0;
  max-width: 420px;
  color: var(--ea-text-secondary);
}

.page-placeholder__hint {
  margin: var(--ea-gap-sm) 0 0;
  color: var(--ea-text-muted);
  font-size: 13px;
}
</style>
