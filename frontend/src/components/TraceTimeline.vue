<template>
  <div class="trace-panel">
    <el-collapse v-model="activeNames">
      <el-collapse-item name="trace">
        <template #title>
          <div class="trace-title">
            <el-icon><CaretRight /></el-icon>
            <span class="trace-title-text">执行轨迹</span>
            <el-tag size="small" type="info" effect="plain">{{ trace.length }} 条记录</el-tag>
            <el-tag v-if="toolNames.length" size="small" type="warning" effect="plain">
              工具 × {{ toolNames.length }}
            </el-tag>
            <el-tag
              v-if="reflectionState"
              size="small"
              :type="reflectionState === 'PASS' ? 'success' : 'danger'"
              effect="plain"
            >
              Reflection {{ reflectionState === 'PASS' ? '通过' : '修订' }}
            </el-tag>
            <span v-if="elapsedMs != null" class="trace-elapsed">{{ formatDuration(elapsedMs) }}</span>
          </div>
        </template>

        <el-timeline class="trace-timeline">
          <el-timeline-item
            v-for="(entry, i) in trace"
            :key="i"
            :type="dotType(entry)"
            :hollow="entry.action === 'final_answer'"
            placement="top"
          >
            <div class="trace-entry">
              <span class="trace-node">{{ entry.node }}</span>

              <!-- 1. 工具调用：detail 为工具名列表 -->
              <template v-if="entry.action === 'tool_call'">
                <span class="trace-action">调用工具</span>
                <el-tag
                  v-for="name in toolListOf(entry)"
                  :key="name"
                  size="small"
                  :type="toolTagType(name)"
                  effect="light"
                  class="trace-tool-tag"
                >
                  {{ name }}
                </el-tag>
              </template>

              <!-- 2. 重复工具调用被拦截（无 detail 键） -->
              <template v-else-if="entry.action === 'blocked_duplicate_tool'">
                <span class="trace-action">重复工具调用被拦截</span>
                <span class="trace-note">复用已有检索结果，未重复执行</span>
              </template>

              <!-- 3. 最终回答 -->
              <template v-else-if="entry.action === 'final_answer'">
                <span class="trace-action">生成最终回答</span>
                <span v-if="typeof entry.detail === 'string' && entry.detail" class="trace-note">{{
                  entry.detail
                }}</span>
              </template>

              <!-- 4. Reflection 审查 -->
              <template v-else-if="entry.node === 'reflection'">
                <span class="trace-action">Reflection 审查</span>
                <el-tag
                  size="small"
                  :type="entry.action === 'REVISE' ? 'danger' : 'success'"
                  effect="light"
                >
                  {{ entry.action === 'REVISE' ? '要求修订，回到 Agent 重答' : '通过' }}
                </el-tag>
                <pre v-if="reflectionText(entry)" class="trace-detail">{{ reflectionText(entry) }}</pre>
              </template>

              <!-- 未知类型：原样展示，保证未来后端新增条目不丢失 -->
              <template v-else>
                <span class="trace-action">{{ entry.action || '未知动作' }}</span>
                <pre v-if="entryHasDetail(entry)" class="trace-detail">{{ detailText(entry) }}</pre>
              </template>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
/**
 * Agent 执行轨迹面板：按后端真实 trace 结构渲染（可展开/收起）。
 * 实际条目形态（agent/graph.py）：
 *   {node:'agent', action:'tool_call', detail:[工具名列表]}
 *   {node:'agent', action:'blocked_duplicate_tool'}          ← 无 detail 键
 *   {node:'agent', action:'final_answer', detail:''}
 *   {node:'reflection', action:'PASS'|'REVISE', detail:审查全文}
 * 注意：后端 trace 不含工具执行结果文本（工具结果只进 LLM 上下文），
 * 面板如实展示"调用了哪些工具"；Reflection 的 detail 含证据审查文本。
 */
import { computed, ref } from 'vue'
import { CaretRight } from '@element-plus/icons-vue'
import { formatDuration } from '@/utils/format'

const props = defineProps({
  trace: { type: Array, default: () => [] },
  elapsedMs: { type: Number, default: null },
})

const activeNames = ref([])

const toolNames = computed(() => {
  const names = []
  for (const e of props.trace) {
    if (e?.action === 'tool_call' && Array.isArray(e.detail)) names.push(...e.detail)
  }
  return names
})

const reflectionState = computed(() => {
  const entries = props.trace.filter((e) => e?.node === 'reflection')
  return entries.length ? entries[entries.length - 1].action : ''
})

function toolListOf(entry) {
  return Array.isArray(entry.detail) ? entry.detail : []
}

function toolTagType(name) {
  if (name === 'knowledge_search') return 'success'
  if (name === 'web_search') return 'primary'
  if (name === 'calculator') return 'warning'
  return 'info'
}

function dotType(entry) {
  if (entry?.action === 'tool_call') return 'warning'
  if (entry?.action === 'blocked_duplicate_tool') return 'warning'
  if (entry?.node === 'reflection') return entry.action === 'REVISE' ? 'danger' : 'success'
  return 'primary'
}

function entryHasDetail(entry) {
  return entry?.detail !== undefined && entry?.detail !== null && entry?.detail !== ''
}

function detailText(entry) {
  return typeof entry.detail === 'string' ? entry.detail : JSON.stringify(entry.detail, null, 2)
}

function reflectionText(entry) {
  if (typeof entry?.detail !== 'string') return ''
  /* detail 为 "PASS" 时无信息量，不展示 */
  return entry.detail.trim() === entry.action ? '' : entry.detail
}
</script>

<style scoped>
.trace-panel {
  margin-top: 10px;
  border-top: 1px dashed var(--ea-border);
  padding-top: 4px;
}

.trace-panel :deep(.el-collapse) {
  border: none;
}

.trace-panel :deep(.el-collapse-item__header) {
  height: 34px;
  line-height: 34px;
  background: transparent;
  border-bottom: none;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.trace-panel :deep(.el-collapse-item__wrap) {
  background: transparent;
  border-bottom: none;
}

.trace-panel :deep(.el-collapse-item__content) {
  padding-bottom: 4px;
}

.trace-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.trace-title .el-icon {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.trace-title-text {
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.trace-elapsed {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.trace-timeline {
  padding: 8px 0 0 4px;
  font-size: 12px;
}

.trace-entry {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  line-height: 24px;
}

.trace-node {
  font-family: var(--el-font-family-mono, Consolas, Monaco, monospace);
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--ea-bg);
  border: 1px solid var(--ea-border);
  border-radius: 3px;
  padding: 0 5px;
  line-height: 20px;
}

.trace-action {
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.trace-note {
  color: var(--el-text-color-secondary);
}

.trace-tool-tag {
  font-family: Consolas, Monaco, monospace;
}

.trace-detail {
  flex-basis: 100%;
  margin: 4px 0 0;
  padding: 8px 10px;
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  background: var(--ea-bg);
  border: 1px solid var(--ea-border);
  border-radius: 4px;
}
</style>
