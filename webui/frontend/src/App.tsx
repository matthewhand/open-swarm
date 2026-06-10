import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Home, Settings, Bot, Book, Users, PlusCircle, MessageSquare, ShieldAlert, Wand2, X } from 'lucide-react'
import { Button, Card, Alert, Badge, LoadingSpinner, ToastProvider } from './components/DaisyUI'
import TeamsPage from './pages/TeamsPage'
import BlueprintsPage from './pages/BlueprintsPage'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import AgentCreatorPage from './pages/AgentCreatorPage'
import { fetchBlueprints, fetchModels } from './lib/api'
import { AuthProvider, useAuth } from './lib/AuthContext'

function App() {
  const [darkMode, setDarkMode] = useState(false)

  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <div className={`min-h-screen ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`} data-theme={darkMode ? 'dark' : 'light'}>
            {/* Navbar */}
            <nav className="bg-base-200 shadow-sm border-b">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                  <div className="flex items-center space-x-6">
                    <Link to="/" className="flex items-center space-x-2">
                      <Bot className="h-8 w-8 text-primary" />
                      <span className="text-xl font-bold">Open Swarm MCP</span>
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
                      <Link to="/agent-creator" className="btn btn-ghost btn-sm">
                        <Wand2 className="h-4 w-4 mr-1" />
                        Agent Creator
                      </Link>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={() => setDarkMode(!darkMode)}
                      className="btn btn-ghost btn-sm"
                    >
                      {darkMode ? 'Light Mode' : 'Dark Mode'}
                    </button>
                    <Link to="/settings" className="btn btn-ghost btn-sm">
                      <Settings className="h-5 w-5" />
                    </Link>
                  </div>
                </div>
              </div>
            </nav>

            {/* Auth failure banner (only shown after a real 401/403) */}
            <AuthErrorBanner />

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/teams" element={<TeamsPage />} />
                <Route path="/blueprints" element={<BlueprintsPage />} />
                <Route path="/agent-creator" element={<AgentCreatorPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </div>

            {/* Bottom Navigation (Mobile) */}
            <div className="btm-nav lg:hidden">
              <Link to="/" className="active">
                <Home className="h-5 w-5" />
                <span className="btm-nav-label">Home</span>
              </Link>
              <Link to="/chat">
                <MessageSquare className="h-5 w-5" />
                <span className="btm-nav-label">Chat</span>
              </Link>
              <Link to="/teams">
                <Users className="h-5 w-5" />
                <span className="btm-nav-label">Teams</span>
              </Link>
              <Link to="/blueprints">
                <Book className="h-5 w-5" />
                <span className="btm-nav-label">Blueprints</span>
              </Link>
              <Link to="/agent-creator">
                <Wand2 className="h-5 w-5" />
                <span className="btm-nav-label">Creator</span>
              </Link>
              <Link to="/settings">
                <Settings className="h-5 w-5" />
                <span className="btm-nav-label">Settings</span>
              </Link>
            </div>
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

  const apiOnline = blueprintsQuery.isSuccess || modelsQuery.isSuccess
  const apiChecking = blueprintsQuery.isPending && modelsQuery.isPending

  return (
    <div className="space-y-6">
      {/* Welcome Alert */}
      <Alert type="info" icon={<Home className="h-5 w-5" />}>
        <span className="font-medium">Welcome to Open Swarm MCP!</span>
        <span className="text-sm">Your AI agent orchestration platform is ready.</span>
      </Alert>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <div className="stat-value text-accent">
              <StatValue
                isPending={modelsQuery.isPending}
                isError={modelsQuery.isError}
                value={modelsQuery.data?.data.length}
              />
            </div>
            <div className="stat-desc">From /v1/models/</div>
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card title="Quick Actions" bordered>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Button variant="primary" size="md" className="w-full">
            <PlusCircle className="h-5 w-5 mr-2" />
            New Team
          </Button>
          <Button variant="secondary" size="md" className="w-full">
            <Book className="h-5 w-5 mr-2" />
            Browse Blueprints
          </Button>
          <Button variant="accent" size="md" className="w-full">
            <Users className="h-5 w-5 mr-2" />
            Team Manager
          </Button>
          <Button variant="info" size="md" className="w-full">
            <Settings className="h-5 w-5 mr-2" />
            Configure
          </Button>
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
