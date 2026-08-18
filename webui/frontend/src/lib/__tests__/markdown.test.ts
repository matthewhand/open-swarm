import { describe, it, expect } from 'vitest'
import { renderSafeMarkdown } from '../markdown'

describe('renderSafeMarkdown', () => {
  it('renders bold and code', () => {
    const html = renderSafeMarkdown('hello **world** and `code`')
    expect(html).toContain('<strong>world</strong>')
    expect(html).toContain('<code>code</code>')
  })

  it('does not execute raw HTML from markdown source', () => {
    const html = renderSafeMarkdown('hi <script>alert(1)</script> **ok**')
    expect(html.toLowerCase()).not.toContain('<script')
    expect(html).toContain('<strong>ok</strong>')
  })

  it('returns empty string for empty input', () => {
    expect(renderSafeMarkdown('')).toBe('')
  })
})
