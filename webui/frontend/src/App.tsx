import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { Home, Users, Book, Settings, Bot, PlusCircle } from 'lucide-react'
import { Card, Alert, Badge, Button } from './components/DaisyUI'

// Lazy loaded page components (simulated for demonstration)
import ChatPage from './pages/ChatPage'
import BuilderPage from './pages/BuilderPage'
import TeamsPage from './pages/TeamsPage'
import AgentCreatorPage from './pages/AgentCreatorPage'
import BlueprintsPage from './pages/BlueprintsPage'

function App() {
  const [isDark, setIsDark] = useState(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches
  )

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
  }, [isDark])

  return (
    <Router>
      <div className="min-h-screen bg-base-200">
        {/* Navigation Bar */}
        <div className="navbar bg-base-100 shadow-sm sticky top-0 z-50">
          <div className="navbar-start">
            <div className="dropdown">
              <label tabIndex={0} className="btn btn-ghost lg:hidden">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h8m-8 6h16" /></svg>
              </label>
              <ul tabIndex={0} className="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
                <li><Link to="/">Dashboard</Link></li>
                <li><Link to="/chat">Chat Interface</Link></li>
                <li><Link to="/teams">Teams</Link></li>
                <li><Link to="/blueprints">Blueprints</Link></li>
                <li><Link to="/builder">Swarm Builder</Link></li>
                <li><Link to="/creator">Agent Creator</Link></li>
                <li><Link to="/settings">Settings</Link></li>
              </ul>
            </div>
            <Link to="/" className="btn btn-ghost normal-case text-xl flex items-center gap-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-content font-bold">
                OS
              </div>
              Open Swarm MCP
            </Link>
          </div>
          <div className="navbar-center hidden lg:flex">
            <ul className="menu menu-horizontal px-1 gap-2">
              <li>
                <Link to="/" className="flex items-center gap-2">
                  <Home className="h-4 w-4" /> Dashboard
                </Link>
              </li>
              <li>
                <Link to="/chat" className="flex items-center gap-2">
                  <Bot className="h-4 w-4" /> Chat
                </Link>
              </li>
              <li>
                <Link to="/teams" className="flex items-center gap-2">
                  <Users className="h-4 w-4" /> Teams
                </Link>
              </li>
              <li>
                <Link to="/blueprints" className="flex items-center gap-2">
                  <Book className="h-4 w-4" /> Blueprints
                </Link>
              </li>
            </ul>
          </div>
          <div className="navbar-end gap-2">
            <label className="swap swap-rotate btn btn-ghost btn-circle">
              <input type="checkbox" checked={isDark} onChange={(e) => setIsDark(e.target.checked)} />
              <svg className="swap-on fill-current w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M5.64,17l-.71.71a1,1,0,0,0,0,1.41,1,1,0,0,0,1.41,0l.71-.71A1,1,0,0,0,5.64,17ZM5,12a1,1,0,0,0-1-1H3a1,1,0,0,0,0,2H4A1,1,0,0,0,5,12Zm7-7a1,1,0,0,0,1-1V3a1,1,0,0,0-2,0V4A1,1,0,0,0,12,5ZM5.64,7.05a1,1,0,0,0,.7.29,1,1,0,0,0,.71-.29,1,1,0,0,0,0-1.41l-.71-.71A1,1,0,0,0,4.93,6.34Zm12,.29a1,1,0,0,0,.7-.29l.71-.71a1,1,0,1,0-1.41-1.41L17,5.64a1,1,0,0,0,0,1.41A1,1,0,0,0,17.66,7.34ZM21,11H20a1,1,0,0,0,0,2h1a1,1,0,0,0,0-2Zm-9,8a1,1,0,0,0-1,1v1a1,1,0,0,0,2,0V20A1,1,0,0,0,12,19ZM18.36,17A1,1,0,0,0,17,18.36l.71.71a1,1,0,0,0,1.41,0,1,1,0,0,0,0-1.41ZM12,6.5A5.5,5.5,0,1,0,17.5,12,5.51,5.51,0,0,0,12,6.5Zm0,9A3.5,3.5,0,1,1,15.5,12,3.5,3.5,0,0,1,12,15.5Z"/></svg>
              <svg className="swap-off fill-current w-5 h-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21.64,13a1,1,0,0,0-1.05-.14,8.05,8.05,0,0,1-3.37.73A8.15,8.15,0,0,1,9.08,5.49a8.59,8.59,0,0,1,.25-2A1,1,0,0,0,8,2.36,10.14,10.14,0,1,0,22,14.05,1,1,0,0,0,21.64,13Zm-9.5,6.69A8.14,8.14,0,0,1,7.08,5.22v.27A10.15,10.15,0,0,0,17.22,15.63a9.79,9.79,0,0,0,2.1-.22A8.11,8.11,0,0,1,12.14,19.69Z"/></svg>
            </label>
            <Link to="/settings" className="btn btn-ghost btn-circle">
              <Settings className="h-5 w-5" />
            </Link>
            <div className="avatar placeholder">
              <div className="bg-neutral text-neutral-content rounded-full w-10">
                <span>AD</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/blueprints" element={<BlueprintsPage />} />
            <Route path="/builder" element={<BuilderPage />} />
            <Route path="/creator" element={<AgentCreatorPage />} />
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
            <Bot className="h-5 w-5" />
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
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const fetchStats = async () => {
      setLoadingStats(true);
      setErrorStats(null);
      try {
        const [bpRes, mRes, tRes] = await Promise.all([
          fetch('/v1/blueprints'),
          fetch('/v1/models'),
          fetch('/teams/export?format=json')
        ]);
        const bpJson: Record<string, unknown> = bpRes.ok ? await bpRes.json() : {data: []};
        const mJson: Record<string, unknown> = mRes.ok ? await mRes.json() : {data: []};
        let tCount = 0;
        if (tRes.ok) {
          const tJson = await tRes.json();
          tCount = tJson && typeof tJson === 'object' ? Object.keys(tJson).length : 0;
        }
        if (!cancelled) {
          setBlueprintCount(Array.isArray(bpJson?.data) ? bpJson.data.length : 0);
          setModelCount(Array.isArray(mJson?.data) ? mJson.data.length : 0);
          setTeamsCount(tCount);
        }
      } catch (e: unknown) {
        if (!cancelled) setErrorStats(`Partial live data (some fetches failed; check vite proxy + backend). ${e instanceof Error ? e.message : String(e)}`);
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
              <div className="stat-value text-primary" aria-live="polite" aria-busy="true" role="status">...</div>
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
              <div className="stat-value text-secondary" aria-live="polite" aria-busy="true" role="status">...</div>
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
              <div className="stat-value text-accent" aria-live="polite" aria-busy="true" role="status">...</div>
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
          <Button variant="primary" size="md" className="w-full" onClick={() => navigate('/creator')}>
            <PlusCircle className="h-5 w-5 mr-2" />
            New Agent
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
