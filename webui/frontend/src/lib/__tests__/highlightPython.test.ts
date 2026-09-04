import { describe, expect, it } from 'vitest'
import { PYTHON_CODE_CLASS, highlightPython } from '../highlightPython'

describe('highlightPython', () => {
  it('escapes HTML in source text', () => {
    const html = highlightPython('value = "<script>alert(1)</script>"')
    expect(html).not.toContain('<script>')
    expect(html).toContain('&lt;script&gt;')
  })

  it('marks keywords, def names, comments, and strings', () => {
    const src = [
      'def classify():',
      '    # YES or NO',
      '    return "YES"',
    ].join('\n')
    const html = highlightPython(src)
    expect(html).toContain('os-py-kw')
    expect(html).toContain('os-py-fn')
    expect(html).toContain('classify')
    expect(html).toContain('os-py-cmt')
    expect(html).toContain('os-py-str')
    expect(PYTHON_CODE_CLASS).toBe('os-code-python')
  })
})
