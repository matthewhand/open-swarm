import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { Button, Card, Badge, Alert } from './components/DaisyUI'
import { Home, Users, Book, Settings, PlusCircle, Moon, Sun, MessageSquare } from 'lucide-react'

// Import existing real pages directly
import ChatPage from './pages/ChatPage'
import BlueprintsPage from './pages/BlueprintsPage'
import BuilderPage from './pages/BuilderPage'
import TeamsPage from './pages/TeamsPage'

// Simple mock for settings
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
  )
}

function Dashboard() {
  const [blueprintCount, setBlueprintCount] = useState<number | null>(null);
  const [modelCount, setModelCount] = useState<number | null>(null);
  const [teamsCount, setTeamsCount] = useState<number | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [errorStats, setErrorStats] = useState<string | null>(null);
  const [apiHealth, setApiHealth] = useState<Record<string, string>>({});
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const fetchStats = async () => {
      setLoadingStats(true);
      setErrorStats(null);
      const health: Record<string, string> = {};
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

      {/* Stats Cards - semi-real from APIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Active Teams</div>
            {loadingStats ? (
              <div className="stat-value text-primary">...</div>
            ) : (
              <div className="stat-value text-primary">{teamsCount ?? 4}</div>
            )}
            <div className="stat-desc">{errorStats ? 'Partial' : 'From /teams/export (live dynamic registry)'}</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Blueprints</div>
            {loadingStats ? (
              <div className="stat-value text-secondary">...</div>
            ) : (
              <div className="stat-value text-secondary">{blueprintCount ?? '?'}</div>
            )}
            <div className="stat-desc">{errorStats ? 'Error loading' : 'From /v1/blueprints (live)'}</div>
          </div>
        </Card>

        <Card compact bordered>
          <div className="stat">
            <div className="stat-title">Models / Agents</div>
            {loadingStats ? (
              <div className="stat-value text-accent">...</div>
            ) : (
              <div className="stat-value text-accent">{modelCount ?? 24}</div>
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
          <Button variant="primary" size="md" className="w-full" onClick={() => navigate('/teams')}>
            <PlusCircle className="h-5 w-5 mr-2" />
            New Team
          </Button>
          <Button variant="secondary" size="md" className="w-full" onClick={() => navigate('/blueprints')}>
            <Book className="h-5 w-5 mr-2" />
            Browse Blueprints
          </Button>
          <Button variant="accent" size="md" className="w-full" onClick={() => navigate('/teams')}>
            <Users className="h-5 w-5 mr-2" />
            Team Manager
          </Button>
          <Button variant="info" size="md" className="w-full" onClick={() => navigate('/settings')}>
            <Settings className="h-5 w-5 mr-2" />
            Configure
          </Button>
        </div>
      </Card>

      {/* System Status */}
      <Card title="System Status" bordered>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 ${apiHealth.models === 'ok' ? 'bg-success' : 'bg-warning'} rounded-full`}></div>
              <span>API Gateway (/v1)</span>
            </div>
            <Badge type={apiHealth.models === 'ok' ? 'success' : 'warning'}>{apiHealth.models === 'ok' ? 'Online' : 'Checking'}</Badge>
          </div>

          <div className="flex items-center justify-between p-3 bg-base-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 ${apiHealth.teams === 'ok' ? 'bg-success' : 'bg-warning'} rounded-full`}></div>
              <span>Team Registry</span>
            </div>
            <Badge type={apiHealth.teams === 'ok' ? 'success' : 'warning'}>{apiHealth.teams === 'ok' ? 'Online' : 'Checking'}</Badge>
          </div>
        </div>
      </Card>
    </div>
  )
}

function App() {
  const [darkMode, setDarkMode] = useState(false);

  // Apply dark mode class to html element
  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }, [darkMode]);

  return (
    <Router>
      <div className="min-h-screen bg-base-100 text-base-content transition-colors duration-200">
        {/* Navigation Bar */}
        <div className="navbar bg-base-200 border-b border-base-300 sticky top-0 z-50">
          <div className="navbar-start">
            <Link to="/" className="btn btn-ghost text-xl">
              <div className="w-8 h-8 rounded bg-primary text-primary-content flex items-center justify-center font-bold mr-2">
                OS
              </div>
              <span className="hidden sm:inline">Open Swarm</span>
            </Link>
          </div>

          <div className="navbar-center hidden lg:flex">
            <ul className="menu menu-horizontal px-1 gap-1">
              <li>
                <Link to="/" className="rounded-lg">
                  <Home className="h-4 w-4" />
                  Dashboard
                </Link>
              </li>
              <li>
                <Link to="/chat" className="rounded-lg">
                  <MessageSquare className="h-4 w-4" />
                  Chat
                </Link>
              </li>
              <li>
                <Link to="/builder" className="rounded-lg">
                  <Book className="h-4 w-4" />
                  Builder
                </Link>
              </li>
              <li>
                <Link to="/teams" className="rounded-lg">
                  <Users className="h-4 w-4" />
                  Teams
                </Link>
              </li>
              <li>
                <Link to="/blueprints" className="rounded-lg">
                  <Book className="h-4 w-4" />
                  Blueprints
                </Link>
              </li>
            </ul>
          </div>

          <div className="navbar-end gap-2">
            <button
              className="btn btn-ghost btn-circle"
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>

            <Link to="/settings" className="btn btn-ghost btn-circle hidden sm:flex">
              <Settings className="h-5 w-5" />
            </Link>

            <div className="dropdown dropdown-end">
              <div tabIndex={0} role="button" className="btn btn-ghost btn-circle avatar placeholder">
                <div className="bg-neutral text-neutral-content rounded-full w-10">
                  <span>U</span>
                </div>
              </div>
              <ul tabIndex={0} className="mt-3 z-[1] p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-52">
                <li><Link to="/settings">Profile & Settings</Link></li>
                <div className="divider my-1"></div>
                <li><a href="/logout">Logout</a></li>
              </ul>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <main className="max-w-7xl mx-auto pb-20 lg:pb-8 pt-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/builder" element={<BuilderPage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/blueprints" element={<BlueprintsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>

        {/* Bottom Navigation (Mobile) */}
        <div className="btm-nav lg:hidden z-50">
          <Link to="/" className="active">
            <Home className="h-5 w-5" />
            <span className="btm-nav-label">Home</span>
          </Link>
          <Link to="/chat">
            <MessageSquare className="h-5 w-5" />
            <span className="btm-nav-label">Chat</span>
          </Link>
          <Link to="/builder">
            <Book className="h-5 w-5" />
            <span className="btm-nav-label">Builder</span>
          </Link>
          <div className="dropdown dropdown-top dropdown-end w-full h-full">
            <div tabIndex={0} role="button" className="flex flex-col items-center justify-center w-full h-full hover:bg-base-200">
              <Users className="h-5 w-5" />
              <span className="btm-nav-label">More</span>
            </div>
            <ul tabIndex={0} className="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52 mb-2">
              <li><Link to="/teams"><Users className="h-4 w-4" /> Teams</Link></li>
              <li><Link to="/blueprints"><Book className="h-4 w-4" /> Blueprints</Link></li>
              <li><Link to="/settings"><Settings className="h-4 w-4" /> Settings</Link></li>
            </ul>
          </div>
        </div>
      </div>
    </Router>
  )
}

export default App
