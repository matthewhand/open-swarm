import React, { useState, useEffect } from 'react';
import { Button, Alert, Badge, LoadingSpinner, Modal } from '../components/DaisyUI';
import { Users, Plus, Search, Play, Trash2, Edit2, Settings, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

interface Team {
  id: string;
  name: string;
  description?: string;
  agents?: number;
  model?: string;
  created_at?: string;
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formLlm, setFormLlm] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [launchResult, setLaunchResult] = useState<string | null>(null);

  useEffect(() => {
    const fetchTeams = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch('/v1/teams');
        if (res.ok) {
          const data = await res.json();
          const list = Array.isArray(data) ? data : (data.data || data.teams || []);
          setTeams(list.map((t: any) => ({
            id: String(t.id || t.name || Math.random()),
            name: t.name || t.id || 'unknown',
            description: t.description || 'No description',
            agents: t.agents?.length || t.agent_count || 0,
            model: t.model || t.llm_profile || 'default',
            created_at: t.created_at || new Date().toISOString(),
          })));
        } else {
          throw new Error('API not available');
        }
      } catch (e) {
        setError('Using demo data (backend /v1/teams not reachable in this env)');
        setTeams([
          {id: 'code-review', name: 'Code Review Team', description: 'Reviews PRs for bugs and style', agents: 3, model: 'gpt-4'},
          {id: 'docs', name: 'Documentation Squad', description: 'Writes and maintains docs', agents: 2, model: 'default'},
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchTeams();
  }, []);

  const filteredTeams = teams.filter(t =>
    t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleLaunch = async (team: Team) => {
    setLaunchResult(`Attempting launch of ${team.name}...`);
    try {
      await new Promise(r => setTimeout(r, 800));
      setLaunchResult(`Launched ${team.name} (simulated via UI - real launch would use CLI or /v1/chat/completions)`);
    } catch {
      setLaunchResult(`Launch request sent for ${team.name}`);
    }
    setTimeout(() => setLaunchResult(null), 4000);
  };

  const handleCreate = async () => {
    if (!formName.trim()) return;
    setActionLoading(true);
    try {
      const res = await fetch('/teams/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ name: formName, description: formDesc, llm_profile: formLlm || 'default' }),
      });
      if (res.ok) {
        setShowCreateModal(false);
        setFormName('');
        setFormDesc('');
        setFormLlm('');
        // Refresh teams list
        const fresh = await fetch('/v1/teams');
        if (fresh.ok) {
          const data = await fresh.json();
          const list = Array.isArray(data) ? data : (data.data || data.teams || []);
          setTeams(list.map((t: any) => ({
            id: String(t.id || t.name || Math.random()),
            name: t.name || t.id || 'unknown',
            description: t.description || 'No description',
            agents: t.agents?.length || t.agent_count || 0,
            model: t.model || t.llm_profile || 'default',
            created_at: t.created_at || new Date().toISOString(),
          })));
        }
      }
    } catch (e) {
      console.error('Create team failed', e);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Users className="h-8 w-8" />
          Team Manager
        </h1>
        <p className="text-gray-500 mt-1">Create and manage your AI teams</p>
      </div>

      {error && <div className="alert alert-warning mb-4">{error}</div>}
      {launchResult && <div className="alert alert-success mb-4">{launchResult}</div>}

      <div className="card bg-base-100 shadow-xl mb-6">
        <div className="card-body">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div className="relative flex-1 max-w-xs">
              <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
              <input
                type="text"
                placeholder="Search teams..."
                className="input input-bordered pl-10 w-full"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="flex gap-2 mt-4 md:mt-0">
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Team
              </button>
              <button className="btn btn-outline">
                <Search className="h-4 w-4 mr-2" />
                Advanced Search
              </button>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTeams.map((team) => (
              <div key={team.id} className="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow">
                <div className="card-body">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-2">
                      <span className="badge badge-primary">{team.agents} agents</span>
                      <span className="badge badge-ghost">{team.model}</span>
                    </div>
                  </div>

                  <h3 className="card-title mb-2">{team.name}</h3>
                  <p className="text-sm text-gray-500 mb-4">{team.description}</p>

                  <div className="text-xs mb-3">
                    <span className="text-gray-500">Created: </span>
                    <span className="font-medium">{new Date(team.created_at).toLocaleDateString()}</span>
                  </div>

                  <div className="card-actions justify-end">
                    <button className="btn btn-outline btn-sm" onClick={() => handleLaunch(team)}>
                      <Play className="h-4 w-4 mr-1" />
                      Launch
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={() => handleLaunch(team)} disabled={actionLoading}>
                      <Play className="h-4 w-4 mr-1" />
                      Launch
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {filteredTeams.length === 0 && (
            <div className="card bg-base-100 shadow-xl text-center py-12 mt-8">
              <div className="mb-4">
                <Users className="h-16 w-16 mx-auto text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No teams found</h3>
              <p className="text-gray-500 mb-4">
                {searchTerm ? 'No teams match your search criteria' : 'Create your first team to get started (persists via backend)'}
              </p>
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Team
              </button>
            </div>
          )}
        </>
      )}

      {/* Create Team Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Team"
      >
        <p className="text-gray-500 mb-4 text-sm">
          Creates a dynamic team via backend POST (persisted to teams.json; appears immediately in /v1/models & /v1/blueprints).
        </p>

        <div className="space-y-4">
          <div>
            <label className="label">
              <span className="label-text">Team Name *</span>
            </label>
            <input
              type="text"
              placeholder="e.g., code-review"
              className="input input-bordered w-full"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              disabled={actionLoading}
            />
            <div className="text-xs text-gray-400 mt-1">Becomes the model id (alphanumeric + dashes).</div>
          </div>

          <div>
            <label className="label">
              <span className="label-text">Description</span>
            </label>
            <textarea
              placeholder="Describe the team's purpose..."
              className="textarea textarea-bordered w-full h-20"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              disabled={actionLoading}
            ></textarea>
          </div>

          <div>
            <label className="label">
              <span className="label-text">LLM Profile (optional)</span>
            </label>
            <input
              type="text"
              placeholder="default or e.g. ollama_local"
              className="input input-bordered w-full"
              value={formLlm}
              onChange={(e) => setFormLlm(e.target.value)}
              disabled={actionLoading}
            />
          </div>
        </div>

        <div className="modal-action flex gap-2 mt-4">
          <button className="btn btn-outline" onClick={() => setShowCreateModal(false)} disabled={actionLoading}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleCreate} disabled={actionLoading || !formName.trim()}>
            {actionLoading ? 'Creating...' : 'Create Team'}
          </button>
        </div>
        <div className="text-xs opacity-60 mt-2">Action uses available /teams/ endpoint (form POST). Refresh to see in other pages.</div>
      </Modal>

      {actionLoading && <div className="fixed bottom-4 right-4"><LoadingSpinner /></div>}
    </div>
  );
}

export default TeamsPage;