import { afterEach, describe, expect, it } from 'vitest'
import {
  KEYBINDING_TIPS_STORAGE_KEY,
  dismissKeybindingTips,
  isKeybindingTipsDismissed,
  pinsShortcutLabel,
  searchShortcutLabel,
} from '../keybindingTips'

describe('keybinding tips persistence', () => {
  afterEach(() => {
    localStorage.removeItem(KEYBINDING_TIPS_STORAGE_KEY)
  })

  it('defaults to not dismissed and persists dismiss best-effort', () => {
    expect(isKeybindingTipsDismissed()).toBe(false)
    dismissKeybindingTips()
    expect(isKeybindingTipsDismissed()).toBe(true)
    expect(localStorage.getItem(KEYBINDING_TIPS_STORAGE_KEY)).toBe('1')
  })

  it('exposes platform-aware Search and pin shortcut labels', () => {
    const search = searchShortcutLabel()
    const pins = pinsShortcutLabel()
    expect(search === '⌘K' || search === 'Ctrl+K').toBe(true)
    expect(pins === '⌥1–9' || pins === 'Alt+1–9').toBe(true)
  })
})
