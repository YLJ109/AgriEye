<script setup>
/**
 * Markdown 渲染组件（marked + DOMPurify 净化）。
 * 用于 AI 生成的治理方案 / 聊天回复等 LLM Markdown 内容，
 * 避免出现 "## 【诊断确认】" 这类原始标记直接展示的问题。
 */
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  source: { type: String, default: '' },
})

marked.setOptions({ gfm: true, breaks: true })

const html = computed(() => DOMPurify.sanitize(marked.parse(props.source || '')))
</script>

<template>
  <div class="md-view" v-html="html"></div>
</template>

<style scoped>
.md-view { font-size: var(--text-sm); line-height: 1.75; color: var(--fg-secondary); word-break: break-word; }

.md-view :deep(h1),
.md-view :deep(h2),
.md-view :deep(h3),
.md-view :deep(h4) {
  color: var(--fg); font-family: var(--font-display);
  font-weight: var(--weight-bold); line-height: 1.4;
  margin: var(--space-4) 0 var(--space-2);
}
.md-view :deep(h1) { font-size: var(--text-lg); }
.md-view :deep(h2) { font-size: var(--text-md); padding-left: var(--space-2); border-left: 3px solid var(--accent); }
.md-view :deep(h3) { font-size: var(--text-sm); color: var(--fg); }
.md-view :deep(h4) { font-size: var(--text-sm); color: var(--fg-secondary); }
.md-view :deep(h1:first-child),
.md-view :deep(h2:first-child),
.md-view :deep(h3:first-child) { margin-top: 0; }

.md-view :deep(p) { margin: 0 0 var(--space-2); }
.md-view :deep(strong) { color: var(--fg); font-weight: var(--weight-semibold); }

.md-view :deep(ul),
.md-view :deep(ol) { margin: 0 0 var(--space-2); padding-left: 1.3em; display: grid; gap: 3px; }
.md-view :deep(ul) { list-style: disc; }
.md-view :deep(ol) { list-style: decimal; }
.md-view :deep(li) { line-height: 1.65; }
.md-view :deep(li::marker) { color: var(--accent); }

.md-view :deep(code) {
  font-family: var(--font-mono); font-size: 0.9em;
  background: var(--bg-muted); color: var(--fg);
  padding: 1px 5px; border-radius: 4px;
}
.md-view :deep(pre) {
  background: var(--bg-muted); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: var(--space-3);
  overflow-x: auto; margin: 0 0 var(--space-2);
}
.md-view :deep(pre code) { background: none; padding: 0; }

.md-view :deep(blockquote) {
  margin: 0 0 var(--space-2); padding: var(--space-2) var(--space-3);
  border-left: 3px solid var(--accent); background: var(--bg-muted);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0; color: var(--fg-muted);
}

.md-view :deep(table) { border-collapse: collapse; width: 100%; margin: 0 0 var(--space-2); font-size: var(--text-xs); }
.md-view :deep(th),
.md-view :deep(td) { border: 1px solid var(--border); padding: 5px 10px; text-align: left; }
.md-view :deep(th) { background: var(--bg-muted); color: var(--fg); font-weight: var(--weight-semibold); }

.md-view :deep(hr) { border: none; border-top: 1px dashed var(--border); margin: var(--space-3) 0; }
.md-view :deep(a) { color: var(--accent); }
</style>
