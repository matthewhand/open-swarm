import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import {
  dispatchSetTheme,
  initialTheme,
  THEME_SET_EVENT,
  THEME_TOGGLE_EVENT,
  type Theme,
} from '../lib/theme'

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(initialTheme)

  useEffect(() => {
    const onSet = (event: Event) => {
      const detail = (event as CustomEvent<Theme>).detail
      if (detail === 'light' || detail === 'dark') setTheme(detail)
    }
    const onToggle = () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
    window.addEventListener(THEME_SET_EVENT, onSet)
    window.addEventListener(THEME_TOGGLE_EVENT, onToggle)
    return () => {
      window.removeEventListener(THEME_SET_EVENT, onSet)
      window.removeEventListener(THEME_TOGGLE_EVENT, onToggle)
    }
  }, [])

  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm btn-square"
      aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      onClick={() => dispatchSetTheme(theme === 'dark' ? 'light' : 'dark')}
    >
      {theme === 'dark' ? (
        <Sun className="h-4 w-4" aria-hidden="true" />
      ) : (
        <Moon className="h-4 w-4" aria-hidden="true" />
      )}
    </button>
  )
}
