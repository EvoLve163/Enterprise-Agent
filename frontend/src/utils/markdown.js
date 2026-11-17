/**
 * Markdown 渲染工具：markdown-it + highlight.js 代码高亮 + DOMPurify 消毒。
 * 仅用于渲染 Agent 返回的 Markdown 文本，禁止渲染任意 HTML（html: false）。
 */
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'
import DOMPurify from 'dompurify'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code class="language-${lang}">${hljs.highlight(code, { language: lang, ignoreIllegals: true }).value}</code></pre>`
      } catch {
        /* fallthrough */
      }
    }
    return `<pre class="hljs"><code class="language-text">${md.utils.escapeHtml(code)}</code></pre>`
  },
})

/* 所有链接在新标签页打开，避免打断聊天页面 */
const defaultLinkOpen =
  md.renderer.rules.link_open ||
  ((tokens, idx, options, env, self) => self.renderToken(tokens, idx, options))

md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

/**
 * 渲染 Markdown 文本为可安全插入的 HTML。
 * @param {string} text Markdown 原文
 * @returns {string} 消毒后的 HTML
 */
export function renderMarkdown(text) {
  if (!text) return ''
  return DOMPurify.sanitize(md.render(text))
}
