import { describe, it, expect } from 'vitest'
import { renderSafeMarkdown } from '../markdown'

describe('renderSafeMarkdown', () => {
  it('renders bold and code', () => {
    const view = renderSafeMarkdown('hello **world** and `code`')
    expect(view).toContain('<strong>world</strong>')
    expect(view).toContain('<code>code</code>')
  })

  it('does not execute raw HTML from markdown source', () => {
    const view = renderSafeMarkdown('hi <script>alert(1)</script> **ok**')
    expect(view.toLowerCase()).not.toContain('<script')
    expect(view).toContain('<strong>ok</strong>')
  })

  it('returns empty string for empty input', () => {
    expect(renderSafeMarkdown('')).toBe('')
  })

  it('highlights Python fenced code', () => {
    const view = renderSafeMarkdown('```python\ndef hello():\n    return "ok"\n```')
    expect(view).toContain('os-code-python')
    expect(view).toContain('os-py-kw')
    expect(view).toContain('def')
    expect(view).toContain('os-py-str')
  })
})
