import { describe, it, expect } from 'vitest'
import { escapeHtml, sanitizeMarkdownHtml } from '../htmlSafe'

describe('escapeHtml', () => {
  it('escapes angle brackets and ampersands', () => {
    expect(escapeHtml(`<script>alert("x")</script>`)).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;',
    )
  })
})

describe('sanitizeMarkdownHtml', () => {
  it('keeps allowlisted formatting tags', () => {
    const out = sanitizeMarkdownHtml('<p>hi <strong>there</strong></p>')
    expect(out).toContain('<strong>there</strong>')
    expect(out).toContain('<p>')
  })

  it('strips script tags and event handlers', () => {
    const out = sanitizeMarkdownHtml(
      '<p onclick="evil()">ok</p><script>alert(1)</script>',
    )
    expect(out).not.toContain('script')
    expect(out).not.toContain('onclick')
    expect(out).toContain('ok')
  })

  it('blocks javascript: hrefs', () => {
    const out = sanitizeMarkdownHtml(
      '<a href="javascript:alert(1)">click</a><a href="https://example.com">safe</a>',
    )
    expect(out).not.toContain('javascript:')
    expect(out).toContain('https://example.com')
  })
})
