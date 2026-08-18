import { marked } from 'marked'
import { escapeHtml, sanitizeMarkdownHtml } from './htmlSafe'

marked.setOptions({ gfm: true, breaks: false })

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
