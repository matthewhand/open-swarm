import React, { useState, useEffect } from 'react';
import { Button, Card, Alert, Badge, LoadingSpinner, Modal } from '../components/DaisyUI';
import { Users, Plus, Trash2, Search, Play } from 'lucide-react';

interface Team {
  id: string | number;
  name: string;
  description: string;
  status: 'active' | 'idle' | 'error';
  members: number;
  created: string;
  llm_profile?: string;
}

// Live teams come from backend dynamic registry via /teams/export (populated into /v1/models + blueprints too)
// Create/delete use the available /teams/ endpoint (csrf_exempt form POST in web_views.team_admin -> register_dynamic_team which saves to teams.json)

const statusColors: Record<string, 'success' | 'warning' | 'error'> = {
  active: 'success',
  idle: 'warning',
  error: 'error',
};

const TeamsPage = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Form state for create
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formLlm, setFormLlm] = useState('');

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      // Prefer /teams/export for rich dynamic team registry data (id, description, llm_profile)
      // These are also surfaced live via /v1/models and /v1/blueprints (merged in views/utils.py)
      const res = await fetch('/teams/export?format=json');
      if (res.ok) {
        const data = await res.json();
        // data shape: { "team-slug": {id, description, llm_profile}, ... }  (object map, not array)
        const list: Team[] = Object.values(data || {}).map((t: unknown) => {
          const tm = t as any;
          return {
            id: tm.id || String(Object.keys(data).find(k => data[k]===tm) || Math.random()),
            name: tm.id || 'unknown-team',
            description: tm.description || 'Dynamic team (no description)',
            status: 'active' as const,
            members: 1,
            created: 'via registry',
            llm_profile: tm.llm_profile || 'default',
          };
        });
        setTeams(list);
      } else {
        throw new Error('Export API failed');
      }
    } catch (e: unknown) {
      setError('Failed to load live teams from /teams/export. Using fallback demo (check backend ENABLE_WEBUI and dynamic registry).');
      // Fallback demo only on error
      setTeams([
        { id: 'code-review', name: 'Code Review Team', description: 'Automated code review and quality assurance (demo)', status: 'active', members: 4, created: '2024-01-15', llm_profile: 'default' },
        { id: 'docs-squad', name: 'Documentation Squad', description: 'Technical writing and documentation generation (demo)', status: 'idle', members: 3, created: '2024-02-20', llm_profile: 'default' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTeams();
  }, []);

  const filteredTeams = teams.filter(team =>
    team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    team.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDelete = async (id: string | number) => {
    if (!window.confirm(`Delete team "${id}"? (calls backend)`)) return;
    setActionLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('action', 'delete');
      fd.append('team_id', String(id));
      // /teams/ is csrf_exempt; form POST triggers deregister_dynamic_team + redirect (side-effect persists)
      await fetch('/teams/', { method: 'POST', body: fd });
      setSuccessMsg(`Deleted ${id}. Registry updated.`);
      await loadTeams();
    } catch (e: unknown) {
      setError('Delete failed (local UI may be stale; try refresh or server admin).');
    } finally {
      setActionLoading(false);
      setTimeout(() => setSuccessMsg(null), 3000);
    }
  };

  const openCreate = () => {
    setFormName('');
    setFormDesc('');
    setFormLlm('');
    setShowCreateModal(true);
    setError(null);
  };

  const handleCreate = async () => {
    if (!formName.trim()) {
      setError('Team name is required');
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('team_name', formName.trim());
      if (formDesc.trim()) fd.append('description', formDesc.trim());
      if (formLlm.trim()) fd.append('llm_profile', formLlm.trim());

      const res = await fetch('/teams/', { method: 'POST', body: fd });
      if (!res.ok) throw new Error('Failed to create team on backend');
      setSuccessMsg(`Team "${formName}" created in dynamic registry.`);
      setShowCreateModal(false);
      await loadTeams();
    } catch (e: unknown) {
      setError('Failed to create team. Ensure django server is running and /teams/ accepts POST.');
    } finally {
      setActionLoading(false);
      setTimeout(() => setSuccessMsg(null), 3000);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 pb-20 lg:pb-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
            <Users className="h-8 w-8" />
            Team Manager
          </h1>
          <p className="text-gray-500">Manage AI agent teams (live syncing with backend /teams/)</p>
        </div>
        <Button variant="primary" onClick={openCreate} disabled={actionLoading}>
          <Plus className="h-5 w-5 mr-2" />
          Create Team
        </Button>
      </div>

      {error && <Alert type="error" className="mb-4" role="alert">{error}</Alert>}
      {successMsg && <Alert type="success" className="mb-4" role="status">{successMsg}</Alert>}

      <div className="mb-6 flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="h-5 w-5 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            placeholder="Search teams..."
            className="input input-bordered pl-10 w-full"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <Badge type="success" className="p-3">Active</Badge>
          <Badge type="warning" className="p-3">Idle</Badge>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12" aria-live="polite" aria-busy="true">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTeams.map((team) => (
            <Card key={team.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="card-title text-xl">{team.name}</h3>
                  <Badge type={statusColors[team.status]}>{team.status}</Badge>
                </div>

                <p className="text-gray-500 text-sm mb-4 line-clamp-2">
                  {team.description}
                </p>

                <div className="space-y-2 mb-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">ID / Key:</span>
                    <span className="font-medium text-xs font-mono">{team.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">LLM Profile:</span>
                    <span className="font-medium">{team.llm_profile || 'default'}</span>
                  </div>
                </div>

                <div className="card-actions justify-end mt-4 pt-4 border-t border-base-200">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-error"
                    onClick={() => handleDelete(team.id)}
                    disabled={actionLoading}
                  >
                    <Trash2 className="h-4 w-4 mr-1" /> Delete
                  </Button>
                  <Button variant="primary" size="sm" disabled={actionLoading}>
                    <Play className="h-4 w-4 mr-1" /> Use in Chat
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create New Team">
        <div className="space-y-4">
          <div className="form-control">
            <label className="label"><span className="label-text">Team ID / Name (Slug)</span></label>
            <input
              type="text"
              className="input input-bordered w-full"
              placeholder="e.g. data-analysis-squad"
              value={formName}
              onChange={e => setFormName(e.target.value)}
            />
          </div>
          <div className="form-control">
            <label className="label"><span className="label-text">Description</span></label>
            <textarea
              className="textarea textarea-bordered h-24"
              placeholder="What does this team do?"
              value={formDesc}
              onChange={e => setFormDesc(e.target.value)}
            ></textarea>
          </div>
          <div className="form-control">
            <label className="label"><span className="label-text">LLM Profile</span></label>
            <input
              type="text"
              className="input input-bordered w-full"
              placeholder="e.g. default, local, smart"
              value={formLlm}
              onChange={e => setFormLlm(e.target.value)}
            />
            <label className="label"><span className="label-text-alt">Must exist in swarm_config.json</span></label>
          </div>

          <div className="modal-action">
            <Button variant="ghost" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleCreate} disabled={actionLoading}>
              {actionLoading ? <LoadingSpinner size="sm" /> : 'Create Team'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default TeamsPage;
