import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import AgentRouterPage from './pages/AgentRouterPage'
import AgentSidebar from './components/AgentSidebar'
import SearchPalette from './components/SearchPalette'
import AgentEditor, { OPEN_AGENT_EDITOR_EVENT, type OpenAgentEditorDetail } from './components/AgentEditor'
import SettingsSheet, {
  OPEN_SETTINGS_EVENT,
  type OpenSettingsDetail,
  type SettingsSection,
} from './components/SettingsSheet'
import { OPEN_LLM_PROFILES_EVENT } from './lib/chromeOverlay'
import { RailChromeProvider, SwipeHint } from './components/RailChrome'
import { ToastProvider } from './components/DaisyUI'
import CommandPalette from './experimental/CommandPalette'
import { isExperimentalEnabled } from './experimental/flags'
import { useLeftEdgeSwipe } from './lib/leftEdgeSwipe'
import { isNarrowViewport, subscribeNarrowViewport } from './lib/narrowViewport'
import { dismissSwipeHint, isSwipeHintDismissed } from './lib/swipeHint'
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

/**
 * Product chrome is Grok-Bot: left rail + the selected agent's chat.
 * `/agents` is Agent Router (own chrome). `/` and `/chat` are the rail + composer.
 * Composer + menu is Compact (REQ-37). Operator Django pages stay on
 * Search / the settings gear.
 */
function App() {
  const [darkMode, setDarkMode] = useState<Theme>(initialTheme)
  const [narrow, setNarrow] = useState(isNarrowViewport)
  const [railOpen, setRailOpen] = useState(() => !isNarrowViewport())
  const [swipeHint, setSwipeHint] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [settingsDetail, setSettingsDetail] = useState<OpenSettingsDetail | null>(null)
  const [agentEditorOpen, setAgentEditorOpen] = useState(false)
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null)

  const openRail = useCallback(() => setRailOpen(true), [])
  const closeRail = useCallback(() => {
    if (!narrow) return
    setRailOpen(false)
  }, [narrow])
  const pickFromRail = useCallback(() => {
    if (!narrow) return
    setRailOpen(false)
    if (!isSwipeHintDismissed()) setSwipeHint(true)
  }, [narrow])
  const dismissHint = useCallback(() => {
    dismissSwipeHint()
    setSwipeHint(false)
  }, [])

  useEffect(() => {
    return subscribeNarrowViewport((next) => {
      setNarrow(next)
      if (next) {
        setRailOpen(false)
      } else {
        setRailOpen(true)
        setSwipeHint(false)
      }
    })
  }, [])

  useLeftEdgeSwipe(narrow && !railOpen && !searchOpen && !settingsOpen, openRail)

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
      const detail = (event as CustomEvent<OpenSettingsDetail>).detail ?? {}
      setSettingsDetail(detail)
      setSettingsOpen(true)
    }
    const onOpenLlmProfiles = () => {
      setSettingsDetail({ section: 'llm-profiles' })
      setSettingsOpen(true)
    }
    const onOpenAgentEditor = (event: Event) => {
      const detail = (event as CustomEvent<OpenAgentEditorDetail>).detail
      setEditingAgentId(detail?.agentId ?? null)
      setAgentEditorOpen(true)
    }
    window.addEventListener(THEME_TOGGLE_EVENT, onToggle)
    window.addEventListener(THEME_SET_EVENT, onSet)
    window.addEventListener('swarm:open-search', onOpenSearch)
    window.addEventListener(OPEN_SETTINGS_EVENT, onOpenSettings)
    window.addEventListener(OPEN_LLM_PROFILES_EVENT, onOpenLlmProfiles)
    window.addEventListener(OPEN_AGENT_EDITOR_EVENT, onOpenAgentEditor)
    return () => {
      window.removeEventListener(THEME_TOGGLE_EVENT, onToggle)
      window.removeEventListener(THEME_SET_EVENT, onSet)
      window.removeEventListener('swarm:open-search', onOpenSearch)
      window.removeEventListener(OPEN_SETTINGS_EVENT, onOpenSettings)
      window.removeEventListener(OPEN_LLM_PROFILES_EVENT, onOpenLlmProfiles)
      window.removeEventListener(OPEN_AGENT_EDITOR_EVENT, onOpenAgentEditor)
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
          blueprintId={settingsDetail?.blueprintId}
          teamId={settingsDetail?.teamId}
          initialSection={settingsDetail?.section}
          definitionKind={settingsDetail?.definitionKind}
          definitionId={settingsDetail?.definitionId}
        />
        <AgentEditor
          isOpen={agentEditorOpen}
          onClose={() => setAgentEditorOpen(false)}
          agentId={editingAgentId}
        />
        <RailChromeProvider value={{ narrow, railOpen, openRail, closeRail }}>
          <div
            className="flex h-screen min-h-0 flex-col bg-base-100 text-base-content"
            data-theme={darkMode === 'dark' ? 'dark' : 'light'}
            data-narrow-viewport={narrow ? 'true' : undefined}
          >
            <a
              href="#os-main"
              className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-content"
            >
              Skip to main content
            </a>
            <div className="flex min-h-0 flex-1">
              <AgentSidebar
                open={narrow ? railOpen : true}
                narrow={narrow}
                onClose={closeRail}
                onPick={pickFromRail}
                onOpenSearch={() => setSearchOpen(true)}
              />
              <div className="flex min-w-0 flex-1 flex-col">
                <main id="os-main" className="min-h-0 min-w-0 flex-1 overflow-hidden" tabIndex={-1}>
                  <Routes>
                    <Route path="/" element={<ChatPage />} />
                    <Route path="/chat" element={<ChatPage />} />
                    <Route path="/chat/*" element={<ChatPage />} />
                    <Route path="/agents" element={<AgentRouterPage />} />
                    <Route path="/agents/*" element={<AgentRouterPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </main>
              </div>
            </div>
            <SwipeHint open={narrow && swipeHint && !railOpen} onDismiss={dismissHint} />
          </div>
        </RailChromeProvider>
      </ToastProvider>
    </Router>
  )
}

export default App
