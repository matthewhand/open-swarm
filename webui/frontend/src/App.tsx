import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { Home, Settings, Bot, Book, Users, PlusCircle } from 'lucide-react'
import { Button, Card, Alert, Badge } from './components/DaisyUI'
import TeamsPage from './pages/TeamsPage'
import BlueprintsPage from './pages/BlueprintsPage'

function App() {
  const [darkMode, setDarkMode] = useState(false)

  return (
    <Router>
      <div className={`min-h-screen ${darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`} data-theme={darkMode ? 'dark' : 'light'}>
        {/* Navbar */}
        <nav className="bg-base-200 shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link to="/" className="flex items-center space-x-2">
                  <Bot className="h-8 w-8 text-primary" />
                  <span className="text-xl font-bold">Open Swarm MCP</span>
                </Link>
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

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/blueprints" element={<BlueprintsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>

        {/* Bottom Navigation (Mobile) */}
        <div className="btm-nav lg:hidden">
          <Link to="/" className="active">
            <Home className="h-5 w-5" />
            <span className="btm-nav-label">Home</span>
          </Link>
          <Link to="/teams">
            <Users className="h-5 w-5" />
            <span className="btm-nav-label">Teams</span>
          </Link>
          <Link to="/blueprints">
            <Book className="h-5 w-5" />
            <span className="btm-nav-label">Blueprints</span>
          </Link>
          <Link to="/settings">
            <Settings className="h-5 w-5" />
            <span className="btm-nav-label">Settings</span>
          </Link>
        </div>
      </div>
    </Router>
  )
}

function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Welcome Alert */}
      <Alert type="info" icon={<Home className="h-5 w-5" />}>
        <span className="font-medium">Welcome to Open Swarm MCP!</span> 
        <span className="text-sm">Your AI agent orchestration platform is ready.</span>
      </Alert>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Active Teams</div>
            <div className="stat-value text-primary">4</div>
            <div className="stat-desc">2 running</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Blueprints</div>
            <div className="stat-value text-secondary">12</div>
            <div className="stat-desc">6 custom</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Agents</div>
            <div className="stat-value text-accent">24</div>
            <div className="stat-desc">8 active</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Completion Rate</div>
            <div className="stat-value text-success">85%</div>
            <div className="stat-desc">↗︎ 5% from last week</div>
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

      {/* Recent Activity */}
      <Card title="Recent Activity" bordered>
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
      </Card>

      {/* System Status */}
      <Card title="System Status" bordered>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-success rounded-full"></div>
              <span>API Gateway</span>
            </div>
            <Badge type="success">Online</Badge>
          </div>

          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-success rounded-full"></div>
              <span>Database</span>
            </div>
            <Badge type="success">Online</Badge>
          </div>

          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-warning rounded-full"></div>
              <span>Cache</span>
            </div>
            <Badge type="warning">Degraded</Badge>
          </div>
        </div>
      </Card>
    </div>
  )
}

function TeamsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Team Management</h1>
      <div className="card bg-base-100 shadow">
        <div className="card-body">
          <div className="flex justify-between items-center mb-4">
            <h2 className="card-title">Your Teams</h2>
            <button className="btn btn-primary">
              <PlusCircle className="h-5 w-5 mr-2" />
              Create Team
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="table w-full">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Members</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Code Review Team</td>
                  <td>3 agents</td>
                  <td><span className="badge badge-success">Active</span></td>
                  <td>
                    <button className="btn btn-sm btn-ghost">Edit</button>
                    <button className="btn btn-sm btn-error">Delete</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

function BlueprintsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Blueprint Library</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card bg-base-100 shadow compact">
          <div className="card-body">
            <h2 className="card-title">Codey</h2>
            <p>Code generation and review assistant</p>
            <div className="card-actions justify-end">
              <button className="btn btn-primary btn-sm">Launch</button>
            </div>
          </div>
        </div>
        <div className="card bg-base-100 shadow compact">
          <div className="card-body">
            <h2 className="card-title">Researcher</h2>
            <p>Web research and analysis tool</p>
            <div className="card-actions justify-end">
              <button className="btn btn-primary btn-sm">Launch</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function SettingsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Settings</h1>
      <div className="card bg-base-100 shadow">
        <div className="card-body">
          <h2 className="card-title">Application Settings</h2>
          <div className="form-control w-full max-w-xs">
            <label className="label">
              <span className="label-text">Theme</span>
            </label>
            <select className="select select-bordered">
              <option>Light</option>
              <option>Dark</option>
              <option>System</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
