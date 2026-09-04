/** Re-export PR 313 highlighter so Agent Router and Chat share one tokenizer. */
import { escapeHtml } from './htmlSafe'
import { highlightPython, isPythonFence } from './highlightPython'

export { highlightPython, isPythonFence }

export function highlightFencedCode(text: string, lang: string | undefined): string {
  if (isPythonFence(lang)) return highlightPython(text)
  return escapeHtml(text)
}
