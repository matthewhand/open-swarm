import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button, Card, Alert, Badge, LoadingSpinner, Modal, ConfirmModal } from '../components/DaisyUI';
import { Users, Plus, Trash2, Search, Play } from 'lucide-react';
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
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (e) {
      const detail = e instanceof Error ? e.message : String(e);
      setError(
        `Could not load teams from /teams/export (${detail}). Use /teams/launch/ or check ENABLE_WEBUI and the dynamic registry.`,
      );
      setTeams([]);
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

  const teamModelId = (team: Team) =>
    typeof team.id === 'string' ? team.id : team.name.toLowerCase().replace(/\s+/g, '-');

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Users className="h-8 w-8" aria-hidden="true" />
            Team Management
          </h1>
          <p className="text-base-content/70 mt-1">Create and manage AI teams from the live dynamic registry</p>
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
          . Bare <code>/teams</code> redirects there when served by Django. Launch opens SPA chat with the team model id preselected (session login required); API clients use{' '}
          <code>/v1/chat/completions</code> with that model id.
        </span>
      </Alert>

      {error && (
        <Alert type="error" role="alert" className="mb-4">
          <div className="space-y-2 text-sm">
            <p>{error}</p>
            <a className="link font-semibold" href="/teams/launch/">
              Open /teams/launch/
            </a>
          </div>
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
        <div className="flex justify-center py-8" aria-live="polite" aria-busy="true" role="status">
          <LoadingSpinner />
          <span className="sr-only">Loading teams</span>
        </div>
      )}

      {/* Teams Grid */}
      {!loading && filteredTeams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredTeams.map((team) => (
            <Card key={team.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  <Badge type={statusColors[team.status]}>
                    {team.status.charAt(0).toUpperCase() + team.status.slice(1)}
                  </Badge>
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

                <h2 className="card-title mb-1">{team.name}</h2>
                <p className="text-sm text-base-content/70 mb-1">{team.description}</p>
                {team.llm_profile && <div className="text-xs text-base-content/50 mb-2">LLM: {team.llm_profile}</div>}

                <div className="divider my-2"></div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-base-content/70">Members:</span>
                    <span className="font-medium">{team.members}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-base-content/70">Created:</span>
                    <span className="font-medium">{team.created}</span>
                  </div>
                </div>

                <div className="card-actions justify-end mt-4">
                  <a
                    className="btn btn-outline btn-sm"
                    href="/teams/launch/"
                    aria-label={`Manage ${team.name} in Django launcher`}
                  >
                    Manage
                  </a>
                  <Link
                    className="btn btn-primary btn-sm"
                    to={`/chat?blueprint=${encodeURIComponent(teamModelId(team))}`}
                    aria-label={`Open chat with team ${team.name}`}
                  >
                    <Play className="h-4 w-4 mr-1" aria-hidden="true" />
                    Launch
                  </Link>
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
            <Users className="h-16 w-16 mx-auto text-base-content/40" aria-hidden="true" />
          </div>
          <h3 className="text-xl font-semibold mb-2">
            {error ? 'Teams unavailable' : 'No teams found'}
          </h3>
          <p className="text-base-content/70 mb-4">
            {searchTerm
              ? 'No teams match your search criteria'
              : error
                ? 'Nothing listed until /teams/export responds.'
                : 'Create your first team to get started (persists via backend)'}
          </p>
          {error ? (
            <a className="btn btn-primary" href="/teams/launch/">
              Open Django launcher
            </a>
          ) : (
            <Button variant="primary" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
              Create Team
            </Button>
          )}
        </Card>
      )}

      {/* Create Team Modal - uses DaisyUI Modal component for consistency */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Team"
      >
        <p className="text-base-content/70 mb-4 text-sm">
          Creates a dynamic team via /v1/teams/ (persisted to teams.json; appears immediately in /v1/models &amp; /v1/blueprints).
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
            <div className="text-xs text-base-content/50 mt-1">Becomes the model id (alphanumeric + dashes).</div>
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
        <p className="text-sm text-base-content/70 mt-2">This action will call the backend to remove the team from the registry.</p>
      </ConfirmModal>

      {actionLoading && (
        <div className="fixed bottom-4 right-4" aria-live="polite" aria-busy="true" role="status">
          <LoadingSpinner />
          <span className="sr-only">Working</span>
        </div>
      )}
    </div>
  );
};

export default TeamsPage;
