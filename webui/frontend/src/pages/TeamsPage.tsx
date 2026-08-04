import { useState, useEffect } from 'react';
import { Button, Card, Alert, Badge, LoadingSpinner, Modal } from '../components/DaisyUI';
import { Users, Plus, Edit, Trash2, Search, Play } from 'lucide-react';

interface Team {
  id: string | number;
  name: string;
  description: string;
  status: 'active' | 'idle' | 'error';
  members: number;
  created: string;
  llm_profile?: string;
}

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

  // Specific item loading states for A11y and deterministic UI
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | number | null>(null);
  const [launchingId, setLaunchingId] = useState<string | number | null>(null);

  // Delete confirm modal state
  const [teamToDelete, setTeamToDelete] = useState<string | number | null>(null);

  // Form state for create
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formLlm, setFormLlm] = useState('');

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/teams/export?format=json');
      if (res.ok) {
        const data = await res.json() as Record<string, unknown>;
        const list: Team[] = Object.values(data || {}).map((t: unknown) => {
          const team = t as Record<string, unknown>;
          return {
            id: String(team.id || Object.keys(data).find(k => data[k] === t) || Math.random()),
            name: String(team.id || 'unknown-team'),
            description: String(team.description || 'Dynamic team (no description)'),
            status: 'active' as const,
            members: 1,
            created: 'via registry',
            llm_profile: team.llm_profile ? String(team.llm_profile) : 'default',
          };
        });
        setTeams(list);
      } else {
        throw new Error('Export API failed');
      }
    } catch (e) {
      setError('Failed to load live teams from /teams/export. Using fallback demo (check backend ENABLE_WEBUI and dynamic registry).');
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

  const confirmDelete = (id: string | number) => {
    setTeamToDelete(id);
  };

  const handleDelete = async () => {
    if (!teamToDelete) return;
    const id = teamToDelete;
    setTeamToDelete(null);
    setDeletingId(id);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('action', 'delete');
      fd.append('team_id', String(id));
      await fetch('/teams/', { method: 'POST', body: fd });
      setSuccessMsg(`Deleted ${id}. Registry updated.`);
      await loadTeams();
    } catch (e) {
      setError('Delete failed (local UI may be stale; try refresh or server admin).');
    } finally {
      setDeletingId(null);
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
    setIsCreating(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append('team_name', formName.trim());
      if (formDesc.trim()) fd.append('description', formDesc.trim());
      if (formLlm.trim()) fd.append('llm_profile', formLlm.trim());
      const res = await fetch('/teams/', { method: 'POST', body: fd });
      if (!res.ok && res.status !== 200) {
        throw new Error('Create POST returned non-ok (but may have side-effected)');
      }
      setShowCreateModal(false);
      setSuccessMsg(`Team "${formName}" created successfully. Appears in /v1/models and /teams/export.`);
      setFormName(''); setFormDesc(''); setFormLlm('');
      await loadTeams();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Create failed via form POST: ${msg}. (Registry change may require page reload or use /teams admin HTML.)`);
    } finally {
      setIsCreating(false);
      setTimeout(() => setSuccessMsg(null), 5000);
    }
  };

  const handleLaunch = (team: Team) => {
    setLaunchingId(team.id);
    const modelId = typeof team.id === 'string' ? team.id : team.name.toLowerCase().replace(/\s+/g, '-');
    setSuccessMsg(`Launch: use model="${modelId}" with /v1/chat/completions (stream=true supported in backend chat_views). See Settings for auth notes.`);
    setTimeout(() => {
      setSuccessMsg(null);
      setLaunchingId((prev) => prev === team.id ? null : prev);
    }, 6000);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Users className="h-8 w-8" />
            Team Management
          </h1>
          <p className="text-gray-500 mt-1">Create and manage your AI teams (live from backend dynamic registry)</p>
        </div>
        <div className="flex gap-2 mt-4 lg:mt-0">
          <Button variant="primary" onClick={openCreate} disabled={isCreating || deletingId !== null}>
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </Button>
          <Button variant="outline" onClick={loadTeams} disabled={loading || isCreating || deletingId !== null}>
            <Search className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      <div aria-live="polite" role="status">
        {error && <Alert type="error" className="mb-4">{error}</Alert>}
        {successMsg && <Alert type="success" className="mb-4">{successMsg}</Alert>}
      </div>

      {/* Search and Filters */}
      <Card bordered className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <label className="label">
              <span className="label-text">Search Teams</span>
            </label>
            <input
              type="text"
              placeholder="Search by name or description..."
              className="input input-bordered w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div>
            <label className="label">
              <span className="label-text">Status Filter</span>
            </label>
            <select aria-label="Status Filter" className="select select-bordered w-full max-w-xs" onChange={() => { /* filter client-side for now */ }}>
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </Card>

      {loading && <div className="flex justify-center py-8"><LoadingSpinner /></div>}

      {/* Teams Grid (live or fallback) */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredTeams.map((team) => (
            <Card key={team.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  <Badge type={statusColors[team.status]}>
                    {team.status.charAt(0).toUpperCase() + team.status.slice(1)}
                  </Badge>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" className="btn-xs" title="Edit (demo)" aria-label={`Edit ${team.name}`}>
                      <Edit className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="btn-xs"
                      onClick={() => confirmDelete(team.id)}
                      disabled={deletingId === team.id || isCreating}
                      loading={deletingId === team.id}
                      aria-label={`Delete ${team.name}`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                <h2 className="card-title mb-1">{team.name}</h2>
                <p className="text-sm text-gray-500 mb-1">{team.description}</p>
                {team.llm_profile && <div className="text-xs text-gray-400 mb-2">LLM: {team.llm_profile}</div>}

                <div className="divider my-2"></div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Members:</span>
                    <span className="font-medium">{team.members}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Created:</span>
                    <span className="font-medium">{team.created}</span>
                  </div>
                </div>

                <div className="card-actions justify-end mt-4">
                  <Button variant="outline" size="sm">
                    View Details
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleLaunch(team)}
                    disabled={launchingId === team.id || deletingId !== null}
                    loading={launchingId === team.id}
                  >
                    <Play className="h-4 w-4 mr-1" />
                    Launch
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredTeams.length === 0 && (
        <Card bordered className="text-center py-12">
          <div className="mb-4">
            <Users className="h-16 w-16 mx-auto text-gray-400" aria-hidden="true" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No teams found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'No teams match your search criteria' : 'Create your first team to get started (persists via backend)'}
          </p>
          <Button variant="primary" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </Button>
        </Card>
      )}

      {/* Create Team Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Team"
      >
        <p className="text-gray-500 mb-4 text-sm">
          Creates a dynamic team via backend POST (persisted to teams.json; appears immediately in /v1/models &amp; /v1/blueprints).
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
              disabled={isCreating}
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
              disabled={isCreating}
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
              disabled={isCreating}
            />
          </div>
        </div>

        <div className="modal-action flex gap-2 mt-4">
          <Button variant="outline" onClick={() => setShowCreateModal(false)} disabled={isCreating}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleCreate} loading={isCreating} disabled={isCreating || !formName.trim()}>
            {isCreating ? 'Creating...' : 'Create Team'}
          </Button>
        </div>
        <div className="text-xs opacity-60 mt-2">Action uses available /teams/ endpoint (form POST). Refresh to see in other pages.</div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={teamToDelete !== null}
        onClose={() => setTeamToDelete(null)}
        title="Delete Team"
      >
        <div className="mb-6">
          <p>Are you sure you want to delete this team? This action cannot be undone.</p>
        </div>
        <div className="modal-action flex gap-2">
          <button className="btn btn-outline" onClick={() => setTeamToDelete(null)}>
            Cancel
          </button>
          <button className={`btn btn-error`} onClick={handleDelete}>
            Delete
          </button>
        </div>
      </Modal>

    </div>
  );
};

export default TeamsPage;
