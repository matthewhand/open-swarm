import { describe, it, expect } from 'vitest'
import { renderSafeMarkdown } from '../markdown'

describe('renderSafeMarkdown', () => {
  it('renders bold and code', () => {
    // eslint-disable-next-line testing-library/render-result-naming-convention
    const result = renderSafeMarkdown('hello **world** and `code`')
    expect(result).toContain('<strong>world</strong>')
    expect(result).toContain('<code>code</code>')
  })

  it('does not execute raw HTML from markdown source', () => {
    // eslint-disable-next-line testing-library/render-result-naming-convention
    const result = renderSafeMarkdown('hi <script>alert(1)</script> **ok**')
    expect(result.toLowerCase()).not.toContain('<script')
    expect(result).toContain('<strong>ok</strong>')
  })

  it('returns empty string for empty input', () => {
    expect(renderSafeMarkdown('')).toBe('')
  })
})
