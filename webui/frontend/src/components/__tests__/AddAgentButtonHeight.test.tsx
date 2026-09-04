import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('Add Agent Button Height (REQ-183)', () => {
  it('defines .os-search-add-btn with height matching .os-rail-search', () => {
    const cssPath = path.resolve(__dirname, '../../index.css')
    const css = fs.readFileSync(cssPath, 'utf-8')

    expect(css).toMatch(/\.os-search-add-btn\s*\{[^}]*?height:\s*2\.25rem;/)
    expect(css).toMatch(/\.os-rail-search\s*\{[^}]*?height:\s*2\.25rem;/)
    expect(css).toMatch(/\.os-search-add-btn::before\s*\{[^}]*?min-width:\s*44px;/)
  })
})
