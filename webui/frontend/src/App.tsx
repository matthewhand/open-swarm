import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { Home, Settings, Bot, Book, Users, PlusCircle } from 'lucide-react'
import { Button, Card, Alert, Badge, LoadingSpinner } from './components/DaisyUI'
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
  const [blueprintCount, setBlueprintCount] = useState<number | null>(null);
  const [modelCount, setModelCount] = useState<number | null>(null);
  const [teamsCount, setTeamsCount] = useState<number | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [errorStats, setErrorStats] = useState<string | null>(null);
  const [apiHealth, setApiHealth] = useState<{models?: string; blueprints?: string; teams?: string}>({});
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const fetchStats = async () => {
      setLoadingStats(true);
      setErrorStats(null);
      const health: {models?: string; blueprints?: string; teams?: string} = {};
      try {
        const [bpRes, mRes, tRes] = await Promise.all([
          fetch('/v1/blueprints'),
          fetch('/v1/models'),
          fetch('/teams/export?format=json')
        ]);
        const bpJson = bpRes.ok ? await bpRes.json() : {data: []};
        const mJson = mRes.ok ? await mRes.json() : {data: []};
        let tCount = 0;
        if (tRes.ok) {
          const tJson = await tRes.json();
          tCount = tJson && typeof tJson === 'object' ? Object.keys(tJson).length : 0;
          health.teams = 'ok';
        }
        if (!cancelled) {
          setBlueprintCount(Array.isArray(bpJson?.data) ? bpJson.data.length : 0);
          setModelCount(Array.isArray(mJson?.data) ? mJson.data.length : 0);
          setTeamsCount(tCount);
          health.models = mRes.ok ? 'ok' : 'fail';
          health.blueprints = bpRes.ok ? 'ok' : 'fail';
          setApiHealth(health);
        }
      } catch (e: unknown) {
        if (!cancelled) setErrorStats('Partial live data (some fetches failed; check vite proxy + backend).');
      } finally {
        if (!cancelled) setLoadingStats(false);
      }
    };
    fetchStats();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome Alert */}
      <Alert type="info" icon={<Home className="h-5 w-5" />}>
        <span className="font-medium">Welcome to Open Swarm MCP!</span> 
        <span className="text-sm">Your AI agent orchestration platform is ready. Real data loaded from backend where possible.</span>
      </Alert>

      {errorStats && (
        <div role="alert" aria-live="assertive">
          <Alert type="warning">{errorStats}</Alert>
        </div>
      )}

      {/* Stats Cards - semi-real from APIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Active Teams</div>
            {loadingStats ? (
              <div className="stat-value text-primary" aria-live="polite" aria-busy="true">...</div>
            ) : (
              <div className="stat-value text-primary" role="status" aria-live="polite">{teamsCount ?? 4}</div>
            )}
            <div className="stat-desc">{errorStats ? 'Partial' : 'From /teams/export (live dynamic registry)'}</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Blueprints</div>
            {loadingStats ? (
              <div className="stat-value text-secondary" aria-live="polite" aria-busy="true">...</div>
            ) : (
              <div className="stat-value text-secondary" role="status" aria-live="polite">{blueprintCount ?? '?'}</div>
            )}
            <div className="stat-desc">{errorStats ? 'Error loading' : 'From /v1/blueprints (live)'}</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Models / Agents</div>
            {loadingStats ? (
              <div className="stat-value text-accent" aria-live="polite" aria-busy="true">...</div>
            ) : (
              <div className="stat-value text-accent" role="status" aria-live="polite">{modelCount ?? 24}</div>
            )}
            <div className="stat-desc">{errorStats ? 'Error' : 'From /v1/models (live)'}</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Completion Rate</div>
            <div className="stat-value text-success">85%</div>
            <div className="stat-desc">Demo / mock</div>
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

// Duplicate local page definitions removed - using imported real pages from ./pages/
// (BlueprintsPage, TeamsPage now contain real API integration + reduced mocks)

function SettingsPage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold mb-6">Settings</h1>
      <Card title="Application Settings" bordered>
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Auth</h3>
            <p className="text-sm">When ENABLE_API_AUTH, use <code>Authorization: Bearer &lt;token&gt;</code> or <code>X-API-Key</code> header.</p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Streaming</h3>
            <p className="text-sm">Backend supports <code>stream: true</code> on <code>/v1/chat/completions</code>. UI can use EventSource / fetch + reader.</p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Teams / Dynamic Registry</h3>
            <p className="text-sm">Teams created via /teams/ POST appear live in /v1/models and /v1/blueprints (merged in utils.py).</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default App
