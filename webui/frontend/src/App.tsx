import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Home, Settings, Bot, Book, Users, History, MessageSquare, PanelLeft } from 'lucide-react'
import ChatPage from './pages/ChatPage'
import Dashboard from './pages/Dashboard'
import AgentSidebar from './components/AgentSidebar'
import TeamsSheet from './components/TeamsSheet'
import CommandPalette from './experimental/CommandPalette'
import { isExperimentalEnabled } from './experimental/flags'

/** EXPERIMENTAL: ⌘K command palette (see experimental/README.md). */
const SHOW_COMMAND_PALETTE = isExperimentalEnabled('command_palette')

/** Theme preference storage key (shared with the Django dark default). */
export const THEME_STORAGE_KEY = 'swarm_theme'

type Theme = 'dark' | 'light'

function initialTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    /* storage unavailable — fall through to the dark default */
  }
  // Default matches the Django operator pages (dark).
  return 'dark'
}

/**
 * SPA mounts Dashboard (`/`) + Chat (`/chat`) only.
 * Operator chrome is Django trailing-slash UI — see docs/ADR-001-primary-ui.md.
 * Do not remount deleted Teams/Blueprints/Settings/Builder/AgentCreator SPA pages.
 */
function App() {
  const [darkMode, setDarkMode] = useState<Theme>(initialTheme)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, darkMode)
    } catch {
      /* persistence is best-effort */
    }
  }, [darkMode])

  // Experimental features (command palette) can request a theme flip without
  // needing prop plumbing — single source of truth stays here.
  useEffect(() => {
    const onToggle = () => setDarkMode((prev) => (prev === 'dark' ? 'light' : 'dark'))
    window.addEventListener('swarm:toggle-theme', onToggle)
    return () => window.removeEventListener('swarm:toggle-theme', onToggle)
  }, [])

  return (
    <Router>
      {SHOW_COMMAND_PALETTE && <CommandPalette />}
      <TeamsSheet />
      <div
        className="flex min-h-screen flex-col bg-base-100 text-base-content"
        data-theme={darkMode === 'dark' ? 'dark' : 'light'}
      >
        <a
          href="#os-main"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-content"
        >
          Skip to main content
        </a>
        <nav className="sticky top-0 z-40 border-b border-base-300 bg-base-200/95 shadow-sm backdrop-blur" aria-label="Primary">
          <div className="flex h-14 items-center justify-between px-3 sm:px-4">
            <div className="flex items-center gap-3 lg:gap-6">
              <button
                type="button"
                className="btn btn-ghost btn-sm btn-square lg:hidden"
                aria-label="Open agents sidebar"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeft className="h-5 w-5" aria-hidden="true" />
              </button>
              <Link to="/" className="flex items-center space-x-2">
                <Bot className="h-6 w-6 text-base-content/80" aria-hidden />
                <span className="text-base font-semibold tracking-tight">Open Swarm</span>
              </Link>
              <div className="hidden lg:flex items-center gap-1">
                <NavLink to="/">Home</NavLink>
                <NavLink to="/chat">Chat</NavLink>
                <a className="btn btn-ghost btn-sm" href="/blueprint-library/">
                  Blueprints
                </a>
                <a className="btn btn-ghost btn-sm" href="/teams/launch/">
                  Teams
                </a>
                <a className="btn btn-ghost btn-sm" href="/sessions/">
                  Sessions
                </a>
                <a className="btn btn-ghost btn-sm" href="/settings/">
                  Settings
                </a>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setDarkMode(darkMode === 'dark' ? 'light' : 'dark')}
                className="btn btn-ghost btn-sm"
                aria-label={darkMode === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              >
                {darkMode === 'dark' ? 'Light' : 'Dark'}
              </button>
              <a href="/settings/" className="btn btn-ghost btn-sm" aria-label="Settings">
                <Settings className="h-5 w-5" aria-hidden="true" />
              </a>
            </div>
          </div>
        </nav>

        <div className="flex min-h-0 flex-1">
          <AgentSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <main id="os-main" className="min-w-0 flex-1 overflow-y-auto pb-20 lg:pb-0" tabIndex={-1}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/chat" element={<ChatPage />} />
              {/* Bare /teams|/blueprints|/settings|/agent-creator|/builder: Django RedirectView in
                  production; unknown SPA paths fall through to dashboard. */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>

        <nav
          className="lg:hidden fixed bottom-0 inset-x-0 z-50 border-t border-base-300 bg-base-200 flex justify-around items-stretch h-16"
          aria-label="Mobile primary"
        >
          {/* Five-tab SPA dock (ADR-001): Settings stays desktop top-nav / gear. */}
          <MobileTab to="/" icon={<Home className="h-5 w-5" />} label="Home" />
          <MobileTab to="/chat" icon={<MessageSquare className="h-5 w-5" />} label="Chat" />
          <MobileTab href="/blueprint-library/" icon={<Book className="h-5 w-5" />} label="Blueprints" />
          <MobileTab href="/teams/launch/" icon={<Users className="h-5 w-5" />} label="Teams" />
          <MobileTab href="/sessions/" icon={<History className="h-5 w-5" />} label="Sessions" />
        </nav>
      </div>
    </Router>
  )
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const { pathname } = useLocation()
  const active = to === '/' ? pathname === '/' : pathname.startsWith(to)
  return (
    <Link
      to={to}
      className={`btn btn-ghost btn-sm ${active ? 'btn-active' : ''}`}
      aria-current={active ? 'page' : undefined}
    >
      {children}
    </Link>
  )
}

function MobileTab({
  to,
  href,
  icon,
  label,
}: {
  to?: string
  href?: string
  icon: React.ReactNode
  label: string
}) {
  const { pathname } = useLocation()
  const target = href || to || '/'
  const active = to
    ? to === '/'
      ? pathname === '/'
      : pathname === to || pathname.startsWith(`${to}/`)
    : false
  const className = `flex flex-col items-center justify-center flex-1 gap-0.5 text-xs min-w-0 px-1 ${
    active ? 'text-base-content font-semibold' : 'text-base-content/55'
  }`
  if (href) {
    return (
      <a href={href} className={className}>
        <span aria-hidden="true">{icon}</span>
        <span className="truncate">{label}</span>
      </a>
    )
  }
  return (
    <Link to={target} className={className} aria-current={active ? 'page' : undefined}>
      <span aria-hidden="true">{icon}</span>
      <span className="truncate">{label}</span>
    </Link>
  )
}

export default App
