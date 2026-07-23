import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Home, Settings, Bot, Book, Users, PlusCircle } from 'lucide-react'
import { Button, Card, Alert, Badge } from './components/DaisyUI'
import TeamsPage from './pages/TeamsPage'
import BlueprintsPage from './pages/BlueprintsPage'
import ChatPage from './pages/ChatPage'

function App() {
  const [darkMode, setDarkMode] = useState(true)

  return (
    <Router>
      <div
        className={`min-h-screen pb-20 lg:pb-0 ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}
        data-theme={darkMode ? 'dark' : 'light'}
      >
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
                >
                  {darkMode ? 'Light' : 'Dark'}
                </button>
                <a href="/settings/" className="btn btn-ghost btn-sm" aria-label="Settings">
                  <Settings className="h-5 w-5" />
                </a>
              </div>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPage />} />
            {/* Client-side leftovers: prefer Django operator UI for primary surfaces */}
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/blueprints" element={<BlueprintsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            {/* Unknown SPA paths: never show a blank shell (was a screenshot P0) */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>

        {/* Fixed horizontal bottom nav on small screens */}
        <nav
          className="lg:hidden fixed bottom-0 inset-x-0 z-50 border-t border-base-300 bg-base-200 flex justify-around items-stretch h-16"
          aria-label="Mobile primary"
        >
          <MobileTab to="/" icon={<Home className="h-5 w-5" />} label="Home" />
          <MobileTab href="/blueprint-library/" icon={<Book className="h-5 w-5" />} label="Blueprints" />
          <MobileTab href="/teams/launch/" icon={<Users className="h-5 w-5" />} label="Teams" />
          <MobileTab href="/sessions/" icon={<PlusCircle className="h-5 w-5" />} label="Sessions" />
          <MobileTab href="/settings/" icon={<Settings className="h-5 w-5" />} label="Settings" />
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
  const active = to === '/' ? pathname === '/' : false
  const className = `flex flex-col items-center justify-center flex-1 gap-0.5 text-xs ${
    active ? 'text-primary font-semibold' : 'text-base-content/70'
  }`
  if (href) {
    return (
      <a href={href} className={className}>
        {icon}
        <span>{label}</span>
      </a>
    )
  }
  return (
    <Link to={target} className={className} aria-current={active ? 'page' : undefined}>
      {icon}
      <span>{label}</span>
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
          This React shell is a lightweight dashboard. Full library, sessions, creators, and
          settings live on the Django paths (trailing slash).
        </span>
      </Alert>

      {errorStats && (
        <Alert type="warning">
          <span className="text-sm">{errorStats}</span>
        </Alert>
      )}

      {/* Stats Cards - semi-real from APIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-base-100 shadow-xl compact">
          <div className="stat">
            <div className="stat-title">Teams</div>
            <div className="stat-value text-primary">
              {loadingStats ? '…' : (teamsCount ?? 0)}
            </div>
            <div className="stat-desc">Registered teams</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-xl compact">
          <div className="stat">
            <div className="stat-title">Blueprints</div>
            <div className="stat-value text-secondary">
              {loadingStats ? '…' : (blueprintCount ?? 0)}
            </div>
            <div className="stat-desc">Discoverable blueprints</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-xl compact">
          <div className="stat">
            <div className="stat-title">Models / Agents</div>
            {loadingStats ? (
              <div className="stat-value text-accent">...</div>
            ) : (
              <div className="stat-value text-accent">{modelCount ?? 24}</div>
            )}
            <div className="stat-desc">{errorStats ? 'Error' : 'From /v1/models (live)'}</div>
          </div>
        </div>

        <div className="card bg-base-100 shadow-xl compact">
          <div className="stat">
            <div className="stat-title">Completion Rate</div>
            <div className="stat-value text-success">85%</div>
            <div className="stat-desc">Demo / mock</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card bg-base-100 shadow-xl">
        <div className="card-body">
          <h2 className="card-title">Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="btn btn-primary w-full">
              <PlusCircle className="h-5 w-5 mr-2" />
              New Team
            </button>
            <button className="btn btn-secondary w-full">
              <Book className="h-5 w-5 mr-2" />
              Browse Blueprints
            </button>
            <button className="btn btn-accent w-full">
              <Users className="h-5 w-5 mr-2" />
              Team Manager
            </button>
            <button className="btn btn-info w-full">
              <Settings className="h-5 w-5 mr-2" />
              Configure
            </button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card bg-base-100 shadow-xl">
        <div className="card-body">
          <h2 className="card-title">Recent Activity</h2>
          <div className="overflow-x-auto">
            <table className="table table-zebra">
              <thead>
                <tr>
                  <th>Team</th>
                  <th>Status</th>
                  <th>Last Activity</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <div className="flex items-center gap-2">
                      <Badge type="success">Active</Badge>
                      <span>Code Review Team</span>
                    </div>
                  </td>
                  <td><Badge type="success">Active</Badge></td>
                  <td className="text-sm text-gray-500">2 minutes ago</td>
                </tr>
                <tr>
                  <td>
                    <div className="flex items-center gap-2">
                      <Badge type="warning">Idle</Badge>
                      <span>Documentation Squad</span>
                    </div>
                  </td>
                  <td><Badge type="warning">Idle</Badge></td>
                  <td className="text-sm text-gray-500">15 minutes ago</td>
                </tr>
                <tr>
                  <td>
                    <div className="flex items-center gap-2">
                      <Badge type="error">Error</Badge>
                      <span>Data Processing</span>
                    </div>
                  </td>
                  <td><Badge type="error">Error</Badge></td>
                  <td className="text-sm text-gray-500">1 hour ago</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* System Status */}
      <Card title="System Status" bordered>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-success rounded-full"></div>
              <span>API Gateway</span>
            </div>
            <span className="badge badge-success">Online</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-success rounded-full"></div>
              <span>Database</span>
            </div>
            <span className="badge badge-success">Online</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-warning rounded-full"></div>
              <span>Cache</span>
            </div>
            <span className="badge badge-warning">Degraded</span>
          </div>
        </div>
      </Card>

      <Card title="Getting started" bordered>
        {(teamsCount === 0 || teamsCount === null) && !loadingStats ? (
          <div className="space-y-3 text-sm">
            <p>No teams registered yet. Launch a blueprint team to expose a custom model id on the API.</p>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                window.location.href = '/teams/launch/'
              }}
            >
              Launch your first team
            </Button>
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

function SettingsPage() {
  // Bare /settings redirects to Django; this route remains only if linked in-app.
  return (
    <div className="max-w-2xl space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-3xl font-bold">Settings</h1>
        <Badge type="warning">Redirected</Badge>
      </div>
      <Alert type="info">
        <span className="text-sm">
          Prefer the full settings dashboard at{' '}
          <a className="link font-semibold" href="/settings/">
            /settings/
          </a>
          .
        </span>
      </Alert>
      <Card title="Application Settings" bordered>
        <div className="space-y-4 text-sm">
          <div>
            <h2 className="font-semibold mb-2">Auth</h2>
            <p>
              When API auth is enabled, send{' '}
              <code>Authorization: Bearer <token></code> or <code>X-API-Key</code>.
            </p>
          </div>
          <div>
            <h2 className="font-semibold mb-2">Streaming</h2>
            <p>
              Use <code>stream: true</code> on <code>/v1/chat/completions</code>.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default App