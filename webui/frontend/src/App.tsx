import { useEffect, useLayoutEffect, useState } from 'react'
import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { PanelLeft } from 'lucide-react'
import ChatPage from './pages/ChatPage'
import AgentSidebar from './components/AgentSidebar'
import SearchPalette from './components/SearchPalette'
import SettingsSheet, { OPEN_SETTINGS_EVENT, type OpenSettingsDetail } from './components/SettingsSheet'
import { ToastProvider } from './components/DaisyUI'
import CommandPalette from './experimental/CommandPalette'
import { isExperimentalEnabled } from './experimental/flags'
import {
  initialTheme,
  persistTheme,
  THEME_SET_EVENT,
  THEME_TOGGLE_EVENT,
  THEME_STORAGE_KEY,
  type Theme,
} from './lib/theme'

/** EXPERIMENTAL: ⌘K command palette (see experimental/README.md). */
const SHOW_COMMAND_PALETTE = isExperimentalEnabled('command_palette')

export { THEME_STORAGE_KEY }

function applyDocumentTheme(theme: Theme) {
  if (typeof document === 'undefined') return
  const value = theme === 'dark' ? 'dark' : 'light'
  const bg = theme === 'dark' ? '#0c0c0c' : '#f4f4f5'
  document.documentElement.setAttribute('data-theme', value)
  document.documentElement.style.backgroundColor = bg
  if (document.body) document.body.style.backgroundColor = bg
}

applyDocumentTheme(initialTheme())

/** Keep query string when aliasing a legacy chat path onto `/chat`. */
export function chatPathWithSearch(search: string): string {
  if (!search) return '/chat'
  return search.startsWith('?') ? `/chat${search}` : `/chat?${search}`
}

/** `/agents` is not a product route — send it to SPA Chat. */
function RedirectAgentsToChat() {
  const { search } = useLocation()
  return <Navigate to={chatPathWithSearch(search)} replace />
}

/**
 * Product chrome is Grok-Bot: left rail + the selected agent's chat.
 * Composer + menu is Compact (REQ-37). Operator Django pages stay on
 * Search / the settings gear.
 * Legacy `/agents` aliases `/chat` (REQ-5d) without restoring Home/Chat top nav.
 * Gear opens the REQ-19 DaisyUI settings sheet over chat.
 */
function App() {
  const [darkMode, setDarkMode] = useState<Theme>(initialTheme)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsBlueprintId, setSettingsBlueprintId] = useState<string | null>(null)

  useLayoutEffect(() => {
    applyDocumentTheme(darkMode)
  }, [darkMode])

  useEffect(() => {
    persistTheme(darkMode)
  }, [darkMode])

  useEffect(() => {
    const onToggle = () => setDarkMode((prev) => (prev === 'dark' ? 'light' : 'dark'))
    const onSet = (event: Event) => {
      const detail = (event as CustomEvent<Theme>).detail
      if (detail === 'light' || detail === 'dark') setDarkMode(detail)
    }
    const onOpenSearch = () => setSearchOpen(true)
    const onOpenSettings = (event: Event) => {
      const detail = (event as CustomEvent<OpenSettingsDetail>).detail
      setSettingsBlueprintId(detail?.blueprintId ?? null)
      setSettingsOpen(true)
    }
    window.addEventListener(THEME_TOGGLE_EVENT, onToggle)
    window.addEventListener(THEME_SET_EVENT, onSet)
    window.addEventListener('swarm:open-search', onOpenSearch)
    window.addEventListener(OPEN_SETTINGS_EVENT, onOpenSettings)
    return () => {
      window.removeEventListener(THEME_TOGGLE_EVENT, onToggle)
      window.removeEventListener(THEME_SET_EVENT, onSet)
      window.removeEventListener('swarm:open-search', onOpenSearch)
      window.removeEventListener(OPEN_SETTINGS_EVENT, onOpenSettings)
    }
  }, [])

  return (
    <Router>
      <ToastProvider>
        {SHOW_COMMAND_PALETTE && <CommandPalette />}
        <SearchPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
        <SettingsSheet
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          blueprintId={settingsBlueprintId}
        />
        <div
          className="flex h-screen min-h-0 flex-col bg-base-100 text-base-content"
          data-theme={darkMode === 'dark' ? 'dark' : 'light'}
        >
          <a
            href="#os-main"
            className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-content"
          >
            Skip to main content
          </a>
          <div className="flex min-h-0 flex-1">
            <AgentSidebar
              open={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              onOpenSearch={() => setSearchOpen(true)}
            />
            <div className="flex min-w-0 flex-1 flex-col">
              <div className="flex h-12 items-center px-2 lg:hidden">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm btn-square"
                  aria-label="Open agents sidebar"
                  onClick={() => setSidebarOpen(true)}
                >
                  <PanelLeft className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>
              <main id="os-main" className="min-h-0 min-w-0 flex-1 overflow-hidden" tabIndex={-1}>
                <Routes>
                  <Route path="/" element={<ChatPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/chat/*" element={<ChatPage />} />
                  <Route path="/agents" element={<RedirectAgentsToChat />} />
                  <Route path="/agents/*" element={<RedirectAgentsToChat />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
            </div>
          </div>
        </div>
      </ToastProvider>
    </Router>
  )
}

export default App
