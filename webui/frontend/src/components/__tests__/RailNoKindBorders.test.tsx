import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('Rail No Kind Borders (REQ-178)', () => {
  it('does not define persistent kind borders for team and remote rows in index.css', () => {
    const cssPath = path.resolve(__dirname, '../../index.css')
    const css = fs.readFileSync(cssPath, 'utf-8')

    expect(css).not.toMatch(/\.os-agent-row--team\s*\{[^}]*?box-shadow:\s*inset 2px 0 0/)
    expect(css).not.toMatch(/\.os-agent-row--remote\s*\{[^}]*?box-shadow:\s*inset 2px 0 0/)
    expect(css).not.toContain('inset 2px 0 0 #6b7c8a')
    expect(css).not.toContain('inset 2px 0 0 #5a7a6a')
  })
})
