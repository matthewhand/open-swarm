import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Home, Settings, Bot, Book, Users, PlusCircle, MessageSquare, ShieldAlert, Wand2, X, Sun, Moon, Wrench } from 'lucide-react'
import { Card, Alert, Badge, LoadingSpinner, ToastProvider } from './components/DaisyUI'
import TeamsPage from './pages/TeamsPage'
import BlueprintsPage from './pages/BlueprintsPage'
import BuilderPage from './pages/BuilderPage'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import AgentCreatorPage from './pages/AgentCreatorPage'
import { fetchBlueprints, fetchModels, fetchTeams } from './lib/api'
import { AuthProvider, useAuth } from './lib/AuthContext'

const THEME_STORAGE_KEY = 'swarm_theme'

function App() {
  // Default to dark so the SPA matches the dark server-rendered (Django) pages;
  // only stay light if the user has explicitly chosen it.
  const [darkMode, setDarkMode] = useState(
    () => localStorage.getItem(THEME_STORAGE_KEY) !== 'light'
  )

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, darkMode ? 'dark' : 'light')
  }, [darkMode])

  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <div className="min-h-screen bg-base-100 text-base-content" data-theme={darkMode ? 'dark' : 'light'}>
            {/* Navbar */}
            <nav className="bg-base-200 shadow-sm border-b border-base-300">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex items-center space-x-6">
                    <Link to="/" className="flex items-center space-x-2">
                      <Bot className="h-8 w-8 text-primary" />
                      <span className="text-xl font-bold">Open Swarm</span>
                    </Link>
                    <div className="hidden lg:flex items-center space-x-1">
                      <Link to="/chat" className="btn btn-ghost btn-sm">
                        <MessageSquare className="h-4 w-4 mr-1" />
                        Chat
                      </Link>
                      <Link to="/teams" className="btn btn-ghost btn-sm">
                        <Users className="h-4 w-4 mr-1" />
                        Teams
                      </Link>
                      <Link to="/blueprints" className="btn btn-ghost btn-sm">
                        <Book className="h-4 w-4 mr-1" />
                        Blueprints
                      </Link>
                      <Link to="/builder" className="btn btn-ghost btn-sm">
                        <Wrench className="h-4 w-4 mr-1" />
                        Builder
                      </Link>
                      <Link to="/agent-creator" className="btn btn-ghost btn-sm">
                        <Wand2 className="h-4 w-4 mr-1" />
                        Agent Creator
                      </Link>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <label
                      className="btn btn-ghost btn-sm btn-circle swap swap-rotate"
                      aria-label={darkMode ? "Switch to light theme" : "Switch to dark theme"}
                    >
                      <input
                        type="checkbox"
                        checked={darkMode}
                        onChange={() => setDarkMode(!darkMode)}
                        aria-label={darkMode ? "Switch to light theme" : "Switch to dark theme"}
                      />
                      <Sun className="swap-on h-5 w-5" aria-hidden="true" />
                      <Moon className="swap-off h-5 w-5" aria-hidden="true" />
                    </label>
                    <Link to="/settings" className="btn btn-ghost btn-sm" aria-label="Settings">
                      <Settings className="h-5 w-5" />
                    </Link>
                  </div>
                </div>
              </div>
            </nav>

            {/* Main Content (pb-24 clears the fixed mobile dock below lg) */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-24 lg:pb-8">
              {/* Auth failure banner (only shown after a real 401/403) */}
              <AuthErrorBanner />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/teams" element={<TeamsPage />} />
                <Route path="/blueprints" element={<BlueprintsPage />} />
                <Route path="/builder" element={<BuilderPage />} />
                <Route path="/agent-creator" element={<AgentCreatorPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>

            {/* Bottom Navigation (Mobile) — DaisyUI 5 "dock" (btm-nav was
                removed in v5); fixed to the viewport bottom below lg. */}
            <nav className="dock lg:hidden" aria-label="Mobile navigation">
              {[
                { to: '/', label: 'Home', icon: Home, end: true },
                { to: '/chat', label: 'Chat', icon: MessageSquare },
                { to: '/teams', label: 'Teams', icon: Users },
                { to: '/blueprints', label: 'Blueprints', icon: Book },
                { to: '/builder', label: 'Builder', icon: Wrench },
                { to: '/agent-creator', label: 'Creator', icon: Wand2 },
                { to: '/settings', label: 'Settings', icon: Settings },
              ].map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) => (isActive ? 'dock-active' : '')}
                >
                  <Icon className="h-5 w-5" />
                  <span className="dock-label">{label}</span>
                </NavLink>
              ))}
            </nav>
          </div>
        </ToastProvider>
      </AuthProvider>
    </Router>
  )
}

function AuthErrorBanner() {
  const { authError, clearAuthError } = useAuth()

  if (!authError) return null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
      <Alert type="error" icon={<ShieldAlert className="h-5 w-5" />}>
        <div className="flex flex-wrap items-center gap-2">
          <span>
            <span className="font-medium">
              Authentication failed ({authError.status}).
            </span>{' '}
            {authError.message}{' '}
            <Link to="/settings" className="link font-medium">
              Set or update your API token in Settings
            </Link>
            .
          </span>
          <button
            className="btn btn-ghost btn-xs ml-auto"
            onClick={clearAuthError}
            aria-label="Dismiss authentication error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </Alert>
    </div>
  )
}

function StatValue({
  isPending,
  isError,
  value,
}: {
  isPending: boolean
  isError: boolean
  value: number | undefined
}) {
  if (isPending) return <LoadingSpinner size="sm" />
  if (isError || value === undefined) return <span title="Failed to load">—</span>
  return <>{value}</>
}

function Dashboard() {
  const blueprintsQuery = useQuery({ queryKey: ['blueprints'], queryFn: fetchBlueprints })
  const modelsQuery = useQuery({ queryKey: ['models'], queryFn: fetchModels })
  const teamsQuery = useQuery({ queryKey: ['teams'], queryFn: fetchTeams })

  const apiOnline =
    blueprintsQuery.isSuccess || modelsQuery.isSuccess || teamsQuery.isSuccess
  const apiChecking =
    blueprintsQuery.isPending && modelsQuery.isPending && teamsQuery.isPending

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold flex items-center gap-2">
        <Home className="h-7 w-7" /> Dashboard
      </h1>

      {/* Welcome Alert */}
      <Alert type="info" icon={<Home className="h-5 w-5" />}>
        <span className="font-medium">Welcome to Open Swarm!&nbsp;</span>
        <span className="text-sm">Your AI agent orchestration platform is ready.</span>
      </Alert>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Blueprints</div>
            <div className="stat-value text-secondary">
              <StatValue
                isPending={blueprintsQuery.isPending}
                isError={blueprintsQuery.isError}
                value={blueprintsQuery.data?.data.length}
              />
            </div>
            <div className="stat-desc">From /v1/blueprints/</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Models</div>
            <div className="stat-value text-primary">
              <StatValue
                isPending={modelsQuery.isPending}
                isError={modelsQuery.isError}
                value={modelsQuery.data?.data.length}
              />
            </div>
            <div className="stat-desc">From /v1/models/</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Teams</div>
            <div className="stat-value text-primary">
              <StatValue
                isPending={teamsQuery.isPending}
                isError={teamsQuery.isError}
                value={teamsQuery.data?.data.length}
              />
            </div>
            <div className="stat-desc">From /v1/teams/</div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card title="Quick Actions" bordered>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Link to="/teams" className="btn btn-primary w-full">
            <PlusCircle className="h-5 w-5 mr-2" />
            New Team
          </Link>
          <Link to="/blueprints" className="btn btn-outline w-full">
            <Book className="h-5 w-5 mr-2" />
            Browse Blueprints
          </Link>
          <Link to="/chat" className="btn btn-outline w-full">
            <MessageSquare className="h-5 w-5 mr-2" />
            Open Chat
          </Link>
          <Link to="/settings" className="btn btn-outline w-full">
            <Settings className="h-5 w-5 mr-2" />
            Configure
          </Link>
        </div>
      </Card>

      {/* Recent Activity intentionally removed: no backend activity feed
          exists yet, and the previous table showed fabricated data. */}

      {/* System Status (derived from live API responses) */}
      <Card title="System Status" bordered>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div
                className={`w-3 h-3 rounded-full ${
                  apiChecking ? 'bg-warning' : apiOnline ? 'bg-success' : 'bg-error'
                }`}
              ></div>
              <span>Backend API</span>
            </div>
            {apiChecking ? (
              <Badge type="warning">Checking…</Badge>
            ) : apiOnline ? (
              <Badge type="success">Online</Badge>
            ) : (
              <Badge type="error">Unreachable</Badge>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}

export default App
