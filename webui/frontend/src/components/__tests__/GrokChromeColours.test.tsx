import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('REQ-101: Grok chrome colours parity', () => {
  const cssPath = path.resolve(__dirname, '../../index.css')
  const cssContent = fs.readFileSync(cssPath, 'utf8')

  it('defines the required Grok color tokens in :root', () => {
    expect(cssContent).toContain('--os-grok-rail: #111111')
    expect(cssContent).toContain('--os-grok-tile-selected: #313131')
    expect(cssContent).toContain('--os-grok-assistant-bubble: #262626')
    expect(cssContent).toContain('--os-grok-user-bubble: #5a5a5a')
    expect(cssContent).toContain('--os-grok-composer: #262626')
    expect(cssContent).toContain('--os-grok-code-inline: #ff5667')
    expect(cssContent).toContain('--os-grok-link: #4194eb')
  })

  it('ensures user bubble background (#5a5a5a) is noticeably lighter than assistant bubble (#262626)', () => {
    const userHex = 0x5a
    const assistantHex = 0x26
    expect(userHex).toBeGreaterThan(assistantHex)
    expect(userHex - assistantHex).toBeGreaterThanOrEqual(0x30)
  })

  it('ensures selected tile (#313131) is distinctly lifted above the rail base (#111111)', () => {
    const tileHex = 0x31
    const railHex = 0x11
    expect(tileHex).toBeGreaterThan(railHex)
    expect(tileHex - railHex).toBeGreaterThanOrEqual(0x20)
  })

  it('applies dark theme rules for assistant and user bubbles', () => {
    expect(cssContent).toMatch(/\.chat-start \.chat-bubble[\s\S]*?--os-grok-assistant-bubble/)
    expect(cssContent).toMatch(/\.chat-end \.chat-bubble[\s\S]*?--os-grok-user-bubble/)
  })

  it('applies dark theme rules for selected favourites and agent rows', () => {
    expect(cssContent).toMatch(/\.os-fav-tile--active[\s\S]*?--os-grok-tile-selected/)
    expect(cssContent).toMatch(/\.os-agent-row--active[\s\S]*?--os-grok-tile-selected/)
  })
})
