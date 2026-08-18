import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Home, Settings, Bot, Book, Users, PlusCircle, History, MessageSquare } from 'lucide-react'
import { Card, Alert, Badge } from './components/DaisyUI'
import ChatPage from './pages/ChatPage'

/**
 * SPA mounts Dashboard (`/`) + Chat (`/chat`) only.
 * Operator chrome is Django trailing-slash UI — see docs/ADR-001-primary-ui.md.
 * Do not remount deleted Teams/Blueprints/Settings/Builder/AgentCreator SPA pages.
 */
function App() {
  const [darkMode, setDarkMode] = useState(true)

  return (
    <Router>
      <div
        className={`min-h-screen pb-20 lg:pb-0 ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}
        data-theme={darkMode ? 'dark' : 'light'}
      >
        <a
          href="#os-main"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-content"
        >
          Skip to main content
        </a>
        <nav className="bg-base-200 shadow-sm border-b sticky top-0 z-40" aria-label="Primary">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-14">
              <div className="flex items-center gap-6">
                <Link to="/" className="flex items-center space-x-2">
                  <Bot className="h-7 w-7 text-primary" aria-hidden />
                  <span className="text-lg font-bold">Open Swarm</span>
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
                  onClick={() => setDarkMode(!darkMode)}
                  className="btn btn-ghost btn-sm"
                  aria-label={darkMode ? 'Switch to light theme' : 'Switch to dark theme'}
                >
                  {darkMode ? 'Light' : 'Dark'}
                </button>
                <a href="/settings/" className="btn btn-ghost btn-sm" aria-label="Settings">
                  <Settings className="h-5 w-5" aria-hidden="true" />
                </a>
              </div>
            </div>
          </div>
        </nav>

        <main id="os-main" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6" tabIndex={-1}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPage />} />
            {/* Bare /teams|/blueprints|/settings|/agent-creator|/builder: Django RedirectView in
                production; unknown SPA paths fall through to dashboard. */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

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
    active ? 'text-primary font-semibold' : 'text-base-content/70'
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

function Dashboard() {
  const [blueprintCount, setBlueprintCount] = useState<number | null>(null)
  const [modelCount, setModelCount] = useState<number | null>(null)
  const [teamsCount, setTeamsCount] = useState<number | null>(null)
  const [loadingStats, setLoadingStats] = useState(true)
  const [errorStats, setErrorStats] = useState<string | null>(null)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchStats = async () => {
      setLoadingStats(true)
      setErrorStats(null)
      try {
        const [bpRes, mRes, tRes, healthRes] = await Promise.all([
          fetch('/v1/blueprints'),
          fetch('/v1/models'),
          fetch('/v1/teams/').catch(() => fetch('/teams/export?format=json')),
          fetch('/health').catch(() => null),
        ])
        const bpJson = bpRes.ok ? await bpRes.json() : { data: [] }
        const mJson = mRes.ok ? await mRes.json() : { data: [] }
        let tCount = 0
        if (tRes && tRes.ok) {
          const tJson = await tRes.json()
          if (Array.isArray(tJson?.data)) tCount = tJson.data.length
          else if (tJson && typeof tJson === 'object') tCount = Object.keys(tJson).length
        }
        if (!cancelled) {
          setBlueprintCount(Array.isArray(bpJson?.data) ? bpJson.data.length : 0)
          setModelCount(Array.isArray(mJson?.data) ? mJson.data.length : 0)
          setTeamsCount(tCount)
          setApiOnline(healthRes ? healthRes.ok : bpRes.ok || mRes.ok)
        }
      } catch {
        if (!cancelled) {
          setErrorStats('Could not load live stats. Is the API running?')
          setApiOnline(false)
        }
      } finally {
        if (!cancelled) setLoadingStats(false)
      }
    }
    fetchStats()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm opacity-70 mt-1">
          Open Swarm — multi-agent blueprints behind an OpenAI-compatible API.
        </p>
      </header>

      <Alert type="info" icon={<Home className="h-5 w-5" />}>
        <span className="font-medium">Welcome to Open Swarm.</span>{' '}
        <span className="text-sm">
          Live counts load from the API when available. Quick Actions open the full operator UI
          (Django) for teams, blueprints, and settings.
        </span>
      </Alert>
      <Alert type="warning">
        <span className="text-sm">
          This React shell is a lightweight dashboard + chat. Full library, sessions, creators, and
          settings live on the Django paths (trailing slash). See ADR-001.
        </span>
      </Alert>

      {errorStats && (
        <Alert type="warning">
          <span className="text-sm">{errorStats}</span>
        </Alert>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Teams</div>
            <div className="stat-value text-primary">
              {loadingStats ? '…' : (teamsCount ?? 0)}
            </div>
            <div className="stat-desc">LLM-profile aliases (/v1/teams)</div>
          </div>
        </Card>
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Blueprints</div>
            <div className="stat-value text-secondary">
              {loadingStats ? '…' : (blueprintCount ?? 0)}
            </div>
            <div className="stat-desc">Discoverable blueprints</div>
          </div>
        </Card>
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Models</div>
            <div className="stat-value text-accent">
              {loadingStats ? '…' : (modelCount ?? 0)}
            </div>
            <div className="stat-desc">Exposed as OpenAI models</div>
          </div>
        </Card>
      </div>

      <Card title="Quick Actions" bordered>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <a href="/teams/launch/" className="btn btn-primary w-full">
            <PlusCircle className="h-5 w-5 mr-2" />
            Launch Team
          </a>
          <a href="/blueprint-library/" className="btn btn-secondary w-full">
            <Book className="h-5 w-5 mr-2" />
            Browse Blueprints
          </a>
          <a href="/teams/" className="btn btn-accent w-full">
            <Users className="h-5 w-5 mr-2" />
            Manage Teams
          </a>
          <a href="/settings/" className="btn btn-info w-full">
            <Settings className="h-5 w-5 mr-2" />
            Settings
          </a>
        </div>
      </Card>

      <Card title="Getting started" bordered>
        {(teamsCount === 0 || teamsCount === null) && !loadingStats ? (
          <div className="space-y-3 text-sm">
            <p>No teams registered yet. Launch a blueprint team to expose a custom model id on the API.</p>
            <a href="/teams/launch/" className="btn btn-primary btn-sm">
              Launch your first team
            </a>
          </div>
        ) : (
          <ul className="list-disc pl-5 text-sm space-y-1 opacity-90">
            <li>
              Point OpenAI clients at <code className="text-xs">/v1</code> with your API token.
            </li>
            <li>
              Browse blueprints at <code className="text-xs">/blueprint-library/</code>, then launch via
              Teams or <code className="text-xs">swarm-cli</code>.
            </li>
            <li>
              Sessions, creators, and full settings live on the Django shell (
              <code className="text-xs">ENABLE_WEBUI=true</code>).
            </li>
            <li>
              SPA chat is at <Link className="link" to="/chat">/chat</Link> (Django session cookie).
            </li>
          </ul>
        )}
      </Card>

      <Card title="API status" bordered>
        <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${
                apiOnline === null ? 'bg-base-300' : apiOnline ? 'bg-success' : 'bg-error'
              }`}
            />
            <span>OpenAI-compatible API</span>
          </div>
          <Badge type={apiOnline ? 'success' : apiOnline === false ? 'error' : 'ghost'}>
            {apiOnline === null ? 'Checking…' : apiOnline ? 'Reachable' : 'Unreachable'}
          </Badge>
        </div>
      </Card>
    </div>
  )
}

export default App
