import { useState, useEffect, useLayoutEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Bot, Book, Users, History, MessageSquare, Settings, Ellipsis, PanelLeft } from 'lucide-react'
import ChatPage from './pages/ChatPage'
import Dashboard from './pages/Dashboard'
import AgentRouterPage from './pages/AgentRouterPage'
import AgentSidebar from './components/AgentSidebar'
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

/** `/chat` is the websocket composer; `/agents` is the Agent Router. */

/**
 * SPA mounts Dashboard (`/`), Chat (`/chat`), and Agent Router (`/agents`).
 * Operator chrome is Django trailing-slash UI — see docs/ADR-001-primary-ui.md.
 * Do not remount deleted Teams/Blueprints/Settings/Builder/AgentCreator SPA pages.
 * Primary tab is Agents; Chat and Django destinations live under More.
 */
function App() {
  const [darkMode, setDarkMode] = useState<Theme>(initialTheme)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useLayoutEffect(() => {
    applyDocumentTheme(darkMode)
  }, [darkMode])

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
        <nav className="sticky top-0 z-40 overflow-visible border-b border-base-300 bg-base-200/95 shadow-sm backdrop-blur" aria-label="Primary">
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
              <Link to="/" className="flex items-center space-x-2" aria-label="Home">
                <Bot className="h-6 w-6 text-base-content/80" aria-hidden />
              </Link>
              <div className="flex items-center gap-1">
                <NavLink to="/agents">Agents</NavLink>
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
              <MoreMenu />
            </div>
          </div>
        </nav>

        <div className="flex min-h-0 flex-1">
          <MaybeBlueprintSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <main id="os-main" className="min-w-0 flex-1 overflow-y-auto pb-20 lg:pb-0" tabIndex={-1}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/*" element={<ChatPage />} />
              <Route path="/agents" element={<AgentRouterPage />} />
              <Route path="/agents/*" element={<AgentRouterPage />} />
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
          <MobileTab to="/agents" icon={<Bot className="h-5 w-5" />} label="Agents" />
          <div className="flex flex-1 items-center justify-center">
            <MoreMenu placement="top" />
          </div>
        </nav>
      </div>
    </Router>
  )
}

function MaybeBlueprintSidebar(props: { open: boolean; onClose: () => void }) {
  const { pathname } = useLocation()
  if (pathname === '/agents' || pathname.startsWith('/agents/')) return null
  return <AgentSidebar {...props} />
}

const MORE_HREFS = [
  { href: '/chat', label: 'Chat', icon: <MessageSquare className="h-4 w-4" />, spa: true },
  { href: '/blueprint-library/', label: 'Blueprints', icon: <Book className="h-4 w-4" /> },
  { href: '/teams/launch/', label: 'Teams', icon: <Users className="h-4 w-4" /> },
  { href: '/sessions/', label: 'Sessions', icon: <History className="h-4 w-4" /> },
  { href: '/settings/', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
] as const

function moreMenuActive(pathname: string): boolean {
  return (
    pathname === '/chat' ||
    pathname.startsWith('/chat/') ||
    pathname.startsWith('/blueprint') ||
    pathname.startsWith('/teams') ||
    pathname.startsWith('/sessions') ||
    pathname.startsWith('/settings')
  )
}

function MoreMenu({ placement = 'bottom' }: { placement?: 'bottom' | 'top' }) {
  const { pathname } = useLocation()
  const extraActive = moreMenuActive(pathname)
  return (
    <div className={`dropdown ${placement === 'top' ? 'dropdown-top dropdown-end' : 'dropdown-end'}`}>
      <button
        type="button"
        tabIndex={0}
        className={`btn btn-ghost btn-sm gap-1 ${extraActive ? 'btn-active' : ''}`}
        aria-label="More"
        aria-haspopup="menu"
      >
        <Ellipsis className="h-4 w-4" aria-hidden="true" />
        More
      </button>
      <ul
        tabIndex={0}
        role="menu"
        className="dropdown-content menu bg-base-200 rounded-box z-50 w-52 p-2 shadow border border-base-300"
      >
        {MORE_HREFS.map((item) => (
          <li key={item.href} role="none">
            {'spa' in item && item.spa ? (
              <Link to={item.href} role="menuitem">
                {item.icon}
                {item.label}
              </Link>
            ) : (
              <a href={item.href} role="menuitem">
                {item.icon}
                {item.label}
              </a>
            )}
          </li>
        ))}
      </ul>
    </div>
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
