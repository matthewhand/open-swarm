import { useEffect, useState } from 'react'
import {
  AVATAR_THEME_SET_EVENT,
  AVATAR_THEME_STORAGE_KEY,
  isAvatarTheme,
  loadAvatarTheme,
  type AvatarTheme,
} from './avatarTheme'

/** Live avatar theme. Updates on this-tab picker changes and other-tab storage. */
export function useAvatarTheme(): AvatarTheme {
  const [theme, setTheme] = useState<AvatarTheme>(loadAvatarTheme)

  useEffect(() => {
    const onSet = (event: Event) => {
      const detail = (event as CustomEvent<AvatarTheme>).detail
      if (isAvatarTheme(detail)) setTheme(detail)
    }
    const onStorage = (event: StorageEvent) => {
      if (event.key === AVATAR_THEME_STORAGE_KEY || event.key === null) {
        setTheme(loadAvatarTheme())
      }
    }
    window.addEventListener(AVATAR_THEME_SET_EVENT, onSet)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener(AVATAR_THEME_SET_EVENT, onSet)
      window.removeEventListener('storage', onStorage)
    }
  }, [])

  return theme
}
