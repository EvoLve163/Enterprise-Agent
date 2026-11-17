<template>
  <div v-if="citations.length" class="citations-box">
    <div class="citations-title">
      <el-icon><Link /></el-icon>
      <span>引用来源</span>
      <span class="citations-count">{{ citations.length }} 条</span>
    </div>
    <div class="citations-list">
      <template v-for="(c, i) in citations" :key="i">
        <!-- 知识库文档：文件名 + 页码 -->
        <span v-if="c.type === 'doc'" class="citation-chip citation-doc" :title="`${c.file} 第${c.page}页`">
          <el-icon><Document /></el-icon>
          <span class="citation-file">{{ c.file }}</span>
          <span class="citation-page">第 {{ c.page }} 页</span>
        </span>

        <!-- 网页：标题 + 链接 -->
        <a
          v-else
          class="citation-chip citation-web"
          :href="c.url"
          target="_blank"
          rel="noopener noreferrer"
          :title="c.url"
        >
          <el-icon><Connection /></el-icon>
          <span class="citation-web-title">{{ c.title }}</span>
        </a>
      </template>
    </div>
  </div>
</template>

<script setup>
/**
 * 引用来源展示：仅展示从回答原文解析到的来源（utils/citations.js），
 * 解析不到则整个区块不渲染 —— 不编造引用。
 */
import { Document, Link, Connection } from '@element-plus/icons-vue'

defineProps({
  citations: { type: Array, default: () => [] },
})
</script>

<style scoped>
.citations-box {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px solid var(--ea-border);
  border-radius: 6px;
  background: var(--ea-bg);
}

.citations-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 6px;
}

.citations-count {
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.citations-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.citation-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 20px;
  cursor: default;
  text-decoration: none;
}

.citation-doc {
  background: var(--el-color-success-light-9);
  border: 1px solid var(--el-color-success-light-7);
  color: var(--el-color-success-dark-2);
}

.citation-web {
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  color: var(--el-color-primary-dark-2);
}

.citation-web:hover {
  border-color: var(--el-color-primary-light-5);
}

.citation-file {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}

.citation-page {
  flex-shrink: 0;
  font-weight: 600;
}

.citation-web-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}
</style>
