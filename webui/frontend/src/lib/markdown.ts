import { marked } from 'marked'
import { escapeHtml, sanitizeMarkdownHtml } from './htmlSafe'
import { highlightPython, isPythonFence } from './highlightPython'

marked.setOptions({ gfm: true, breaks: false })

marked.use({
  renderer: {
    code({ text, lang }: { text: string; lang?: string }) {
      const language = String(lang || '').trim()
      const body = isPythonFence(language) ? highlightPython(text) : escapeHtml(text)
      const cls = language
        ? `language-${escapeHtml(language.split(/[\s{]/)[0] || '')}`
        : ''
      const extra = isPythonFence(language) ? ' os-code-python' : ''
      return `<pre class="os-code${extra}"><code class="${cls}">${body}</code></pre>`
    },
  },
})

/** Parse markdown then allowlist-sanitize for safe innerHTML. */
export function renderSafeMarkdown(source: string): string {
  const text = String(source ?? '')
  if (!text) return ''
  try {
    const parsed = marked.parse(text, { async: false })
    return sanitizeMarkdownHtml(typeof parsed === 'string' ? parsed : String(parsed))
  } catch {
    return escapeHtml(text)
  }
}
