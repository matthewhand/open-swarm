import { useState, useEffect } from 'react';
import { Button, Card, Alert, Badge, LoadingSpinner, Modal, ConfirmModal } from '../components/DaisyUI';
import { Users, Plus, Edit, Trash2, Search, Play } from 'lucide-react';
import { createTeam, deleteTeam } from '../lib/api';

interface Team {
  id: string | number;
  name: string;
  description: string;
  status: 'active' | 'idle' | 'error';
  members: number;
  created: string;
  llm_profile?: string;
}

interface ApiTeam {
  id?: string | number;
  description?: string;
  llm_profile?: string;
}

// Live teams come from backend dynamic registry via /teams/export (populated into /v1/models + blueprints too)
// Create/delete use CSRF-safe JSON API (/v1/teams/) rather than the session-CSRF /teams/ form admin.

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
  const [teamToDelete, setTeamToDelete] = useState<string | number | null>(null);

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
          const apiTeam = t as ApiTeam;
          return {
            id: apiTeam.id || String(Object.keys(data).find(k => data[k] === apiTeam) || Math.random()),
            name: String(apiTeam.id || 'unknown-team'),
            description: apiTeam.description || 'Dynamic team (no description)',
            status: 'active' as const,
            members: 1,
            created: 'via registry',
            llm_profile: apiTeam.llm_profile || 'default',
          };
        });
        setTeams(list);
      } else {
        throw new Error('Export API failed');
      }
    } catch (e) {
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

  const handleDelete = async () => {
    if (!teamToDelete) return;
    setActionLoading(true);
    setError(null);
    try {
      await deleteTeam(String(teamToDelete));
      setSuccessMsg(`Deleted ${teamToDelete}. Registry updated.`);
      await loadTeams();
    } catch (e) {
      setError('Delete failed (local UI may be stale; try refresh or server admin).');
    } finally {
      setActionLoading(false);
      setTeamToDelete(null);
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
      await createTeam({
        name: formName.trim(),
        ...(formDesc.trim() ? { description: formDesc.trim() } : {}),
        ...(formLlm.trim() ? { llm_profile: formLlm.trim() } : {}),
      });
      setShowCreateModal(false);
      setSuccessMsg(`Team "${formName}" created successfully. Appears in /v1/models and /teams/export.`);
      setFormName(''); setFormDesc(''); setFormLlm('');
      await loadTeams();
    } catch (e: unknown) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      setError(`Create failed via /v1/teams/: ${errorMessage}. (Try refresh or the /teams admin HTML.)`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setSuccessMsg(null), 5000);
    }
  };

  const handleLaunch = (team: Team) => {
    const modelId = typeof team.id === 'string' ? team.id : team.name.toLowerCase().replace(/\s+/g, '-');
    // Real launch uses the team id as model in the OpenAI compatible endpoint.
    // Streaming supported server-side: POST /v1/chat/completions { "model": "...", "messages": [...], "stream": true }
    // Auth: pass Authorization: Bearer <token> (from SWARM_API_KEY or equiv) or X-API-Key when enabled.
    setSuccessMsg(`Launch: use model="${modelId}" with /v1/chat/completions (stream=true supported in backend chat_views). See Settings for auth notes.`);
    setTimeout(() => setSuccessMsg(null), 6000);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Users className="h-8 w-8" aria-hidden="true" />
            Team Management
          </h1>
          <p className="text-gray-500 mt-1">Create and manage your AI teams (live from backend dynamic registry)</p>
        </div>
        <div className="flex gap-2 mt-4 lg:mt-0">
          <Button variant="primary" onClick={openCreate} disabled={actionLoading}>
            <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
            Create Team
          </Button>
          <Button variant="outline" onClick={loadTeams} disabled={loading}>
            <Search className="h-4 w-4 mr-2" aria-hidden="true" />
            Refresh
          </Button>
        </div>
      </div>

      <Alert type="info" role="status" className="mb-4">
        <span className="text-sm">
          Prefer the full operator UI at{' '}
          <a className="link font-semibold" href="/teams/launch/">
            /teams/launch/
          </a>
          . Bare <code>/teams</code> redirects there when served by Django.
        </span>
      </Alert>

      {error && (
        <Alert type="error" role="alert" className="mb-4">
          {error}
        </Alert>
      )}
      {successMsg && (
        <Alert type="success" role="status" className="mb-4">
          {successMsg}
        </Alert>
      )}

      {/* Search and Filters */}
      <Card bordered className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <label htmlFor="teams-search" className="label">
              <span className="label-text">Search Teams</span>
            </label>
            <input
              id="teams-search"
              type="search"
              placeholder="Search by name or description..."
              className="input input-bordered w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="teams-status-filter" className="label">
              <span className="label-text">Status Filter</span>
            </label>
            <select
              id="teams-status-filter"
              className="select select-bordered w-full max-w-xs"
              defaultValue=""
              aria-label="Status Filter"
              onChange={() => { /* filter client-side for now */ }}
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </Card>

      {loading && (
        <div className="flex justify-center py-8" aria-live="polite" aria-busy="true">
          <LoadingSpinner />
        </div>
      )}

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
                    <Button
                      variant="ghost"
                      size="sm"
                      className="btn-xs"
                      title="Edit (demo)"
                      aria-label={`Edit ${team.name}`}
                    >
                      <Edit className="h-3 w-3" aria-hidden="true" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="btn-xs"
                      onClick={() => setTeamToDelete(team.id)}
                      disabled={actionLoading}
                      aria-label={`Delete ${team.name}`}
                    >
                      <Trash2 className="h-3 w-3" aria-hidden="true" />
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
                  <Button variant="primary" size="sm" onClick={() => handleLaunch(team)} disabled={actionLoading}>
                    <Play className="h-4 w-4 mr-1" aria-hidden="true" />
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
        <Card bordered className="text-center py-12" role="status">
          <div className="mb-4">
            <Users className="h-16 w-16 mx-auto text-gray-400" aria-hidden="true" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No teams found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'No teams match your search criteria' : 'Create your first team to get started (persists via backend)'}
          </p>
          <Button variant="primary" onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
            Create Team
          </Button>
        </Card>
      )}

      {/* Create Team Modal - uses DaisyUI Modal component for consistency */}
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
            <label htmlFor="create-team-name" className="label">
              <span className="label-text">Team Name *</span>
            </label>
            <input
              id="create-team-name"
              type="text"
              placeholder="e.g., code-review"
              className="input input-bordered w-full"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              disabled={actionLoading}
              required
              autoFocus
            />
            <div className="text-xs text-gray-400 mt-1">Becomes the model id (alphanumeric + dashes).</div>
          </div>

          <div>
            <label htmlFor="create-team-desc" className="label">
              <span className="label-text">Description</span>
            </label>
            <textarea
              id="create-team-desc"
              placeholder="Describe the team's purpose..."
              className="textarea textarea-bordered w-full h-20"
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              disabled={actionLoading}
            ></textarea>
          </div>

          <div>
            <label htmlFor="create-team-llm" className="label">
              <span className="label-text">LLM Profile (optional)</span>
            </label>
            <input
              id="create-team-llm"
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
          <Button variant="outline" onClick={() => setShowCreateModal(false)} disabled={actionLoading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleCreate} loading={actionLoading} disabled={actionLoading || !formName.trim()}>
            {actionLoading ? 'Creating...' : 'Create Team'}
          </Button>
        </div>
        <div className="text-xs opacity-60 mt-2">Action uses /v1/teams/ JSON API. Refresh to see in other pages.</div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={teamToDelete !== null}
        onClose={() => setTeamToDelete(null)}
        onConfirm={handleDelete}
        title="Delete Team"
        confirmText="Delete"
        confirmVariant="error"
      >
        <p>Are you sure you want to delete team "{teamToDelete}"?</p>
        <p className="text-sm text-gray-500 mt-2">This action will call the backend to remove the team from the registry.</p>
      </ConfirmModal>

      {actionLoading && (
        <div className="fixed bottom-4 right-4" aria-live="polite" aria-busy="true">
          <LoadingSpinner />
        </div>
      )}
    </div>
  );
};

export default TeamsPage;
