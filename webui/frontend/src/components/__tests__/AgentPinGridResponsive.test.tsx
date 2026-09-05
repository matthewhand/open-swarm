import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('REQ-206: Pinned grid columns adapt to sidepane width (1 / 2 / 3)', () => {
  const cssPath = path.resolve(__dirname, '../../index.css')
  const cssContent = fs.readFileSync(cssPath, 'utf-8')

  it('declares container-type: inline-size on .os-agent-sidebar', () => {
    expect(cssContent).toMatch(/\.os-agent-sidebar\s*\{[^}]*container-type:\s*inline-size/s)
  })

  it('defines container queries for 1, 2, and 3 columns on .os-fav-grid', () => {
    // Default 2-column layout
    expect(cssContent).toMatch(/\.os-fav-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/s)

    // Narrow rail container query: 1 column
    expect(cssContent).toMatch(/@container\s*\([^)]*max-width:\s*200px[^)]*\)\s*\{[^}]*\.os-fav-grid\s*\{[^}]*grid-template-columns:\s*1fr/s)

    // Wide rail container query: 3 columns
    expect(cssContent).toMatch(/@container\s*\([^)]*min-width:\s*320px[^)]*\)\s*\{[^}]*\.os-fav-grid\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/s)
  })

  it('preserves single-column collapsed avatar-only mode', () => {
    expect(cssContent).toMatch(/\.os-agent-sidebar--avatar-only\s+\.os-fav-grid\s*\{[^}]*grid-template-columns:\s*1fr/s)
  })
})
