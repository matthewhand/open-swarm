import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('REQ-196: Collapsed sidepane vertical alignment for Support and peer rows', () => {
  it('defines vertical centering, matching row heights, and hides role badge in avatar-only mode', () => {
    const cssPath = path.resolve(__dirname, '../../index.css')
    const css = fs.readFileSync(cssPath, 'utf8')

    // Expect .os-agent-sidebar--avatar-only .os-agent-row to have centering and height
    const avatarOnlyRowMatch = css.match(
      /\.os-agent-sidebar--avatar-only\s+\.os-agent-row\s*\{([^}]+)\}/
    )
    expect(avatarOnlyRowMatch).toBeTruthy()
    const rowRules = avatarOnlyRowMatch![1]
    expect(rowRules).toMatch(/justify-content:\s*center/)
    expect(rowRules).toMatch(/align-items:\s*center/)
    expect(rowRules).toMatch(/height:\s*2\.75rem/)

    // Expect .os-agent-sidebar--avatar-only .os-agent-row__avatar-slot to center and reset margin
    const avatarSlotMatch = css.match(
      /\.os-agent-sidebar--avatar-only\s+\.os-agent-row__avatar-slot\s*\{([^}]+)\}/
    )
    expect(avatarSlotMatch).toBeTruthy()
    const slotRules = avatarSlotMatch![1]
    expect(slotRules).toMatch(/margin-top:\s*0/)
    expect(slotRules).toMatch(/align-self:\s*center/)

    // Expect .os-agent-sidebar--avatar-only .os-agent-role-badge to be hidden
    const roleBadgeMatch = css.match(
      /\.os-agent-sidebar--avatar-only\s+\.os-agent-role-badge\s*\{([^}]+)\}/
    )
    expect(roleBadgeMatch).toBeTruthy()
    const badgeRules = roleBadgeMatch![1]
    expect(badgeRules).toMatch(/display:\s*none/)
  })
})
