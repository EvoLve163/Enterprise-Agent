/**
 * 引用来源解析：从 Agent 回答原文中解析知识库文档与网页链接来源。
 *
 * 依据（不编造引用）：
 * - knowledge_search 工具输出格式为 "[依据i] 来源：{file}.pdf，第{page}页"，
 *   LLM 回答通常复述该格式 → 用正则匹配 "来源：xxx.pdf，第N页"。
 * - web_search 工具返回 "标题：... 链接：..."，LLM 回答常以 Markdown 链接
 *   [标题](URL) 或 "链接：URL" 行引用 → 用正则提取。
 * 解析不到就返回空数组，前端不展示引用区。
 */

/**
 * @typedef {{type:'doc', file:string, page:number}} DocCitation
 * @typedef {{type:'web', title:string, url:string}} WebCitation
 */

/**
 * 从回答文本解析引用来源（自动去重）。
 * @param {string} answer Agent 回答原文
 * @returns {(DocCitation|WebCitation)[]}
 */
export function extractCitations(answer = '') {
  if (!answer) return []
  const docs = []
  const webs = []
  const seenDoc = new Set()
  const seenWeb = new Set()
  let m

  /* 1. 知识库文档：[依据1] 来源：`demo_company_policy.pdf`，第 3 页
     兼容：文件名被反引号/引号包裹、逗号省略（实测 LLM 常用行内代码包裹文件名） */
  const kbRe = /来源[：:]\s*([^\s，,。；;]*?\.pdf)[`'"“”]?\s*[，,]?\s*第\s*(\d+)\s*页/gi
  while ((m = kbRe.exec(answer)) !== null) {
    const file = m[1].replace(/[`'"“”]/g, '')
    const key = `${file.toLowerCase()}#${m[2]}`
    if (!seenDoc.has(key)) {
      seenDoc.add(key)
      docs.push({ type: 'doc', file, page: Number(m[2]) })
    }
  }

  /* 2. Markdown 链接：[标题](https://...) —— 标题即网页标题 */
  const mdRe = /\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g
  while ((m = mdRe.exec(answer)) !== null) {
    const url = m[2]
    if (!seenWeb.has(url)) {
      seenWeb.add(url)
      webs.push({ type: 'web', title: m[1].trim() || url, url })
    }
  }

  /* 3. 行内链接：链接：https://... 或 来源网站：https://... */
  const lineRe = /(?:链接|来源网站|原文地址)[：:]\s*(https?:\/\/\S+)/g
  while ((m = lineRe.exec(answer)) !== null) {
    const url = m[1].replace(/[。，,；;）)]+$/, '')
    if (!seenWeb.has(url)) {
      seenWeb.add(url)
      webs.push({ type: 'web', title: url, url })
    }
  }

  return [...docs, ...webs]
}
