import { afterEach, describe, expect, it } from 'vitest'
import {
  AVATAR_THEME_SET_EVENT,
  AVATAR_THEME_STORAGE_KEY,
  defaultAvatarTheme,
  loadAvatarTheme,
  saveAvatarTheme,
} from '../avatarTheme'

describe('avatar theme persist', () => {
  afterEach(() => {
    localStorage.removeItem(AVATAR_THEME_STORAGE_KEY)
  })

  it('defaults to Default and persists Blobs like hostname', () => {
    expect(loadAvatarTheme()).toBe(defaultAvatarTheme())
    expect(loadAvatarTheme()).toBe('default')
    expect(saveAvatarTheme('blobs')).toBe('blobs')
    expect(localStorage.getItem(AVATAR_THEME_STORAGE_KEY)).toBe('blobs')
    expect(loadAvatarTheme()).toBe('blobs')
  })

  it('treats unknown values as Default and clears storage for Default', () => {
    expect(saveAvatarTheme('not-a-theme')).toBe('default')
    expect(localStorage.getItem(AVATAR_THEME_STORAGE_KEY)).toBeNull()
    localStorage.setItem(AVATAR_THEME_STORAGE_KEY, 'blobs')
    expect(saveAvatarTheme('default')).toBe('default')
    expect(localStorage.getItem(AVATAR_THEME_STORAGE_KEY)).toBeNull()
  })

  it('dispatches a same-tab event so pickers update without reload', () => {
    const seen: string[] = []
    const onSet = (event: Event) => {
      seen.push((event as CustomEvent<string>).detail)
    }
    window.addEventListener(AVATAR_THEME_SET_EVENT, onSet)
    saveAvatarTheme('blobs')
    window.removeEventListener(AVATAR_THEME_SET_EVENT, onSet)
    expect(seen).toEqual(['blobs'])
  })
})
