import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('REQ-187: Hidden Bots drop target highlights on DnD hover', () => {
  it('applies dashed outline and background highlight when data-drag-over or os-hidden-bots--active', () => {
    const cssPath = path.resolve(__dirname, '../../index.css')
    const css = fs.readFileSync(cssPath, 'utf8')

    // Find the rule for .os-hidden-bots[data-drag-over], .os-hidden-bots.os-hidden-bots--active
    const match = css.match(
      /\.os-hidden-bots\[data-drag-over\],\s*\.os-hidden-bots\.os-hidden-bots--active\s*\{([^}]+)\}/
    )
    expect(match).toBeTruthy()
    const rules = match![1]
    expect(rules).toMatch(/outline:\s*1\.5px dashed/)
    expect(rules).toMatch(/background:\s*color-mix/)
  })
})
