import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Alert, Badge, LoadingSpinner, Modal } from '../components/DaisyUI';
import { Users, Plus, Search, Play, Trash2, Edit } from 'lucide-react';

interface Team {
  id: string | number;
  name: string;
  description: string;
  members: number;
  created: string;
  status: 'active' | 'idle' | 'error';
  llm_profile?: string;
}

const statusColors: Record<Team['status'], 'success' | 'warning' | 'error'> = {
  active: 'success',
  idle: 'warning',
  error: 'error',
};

const fallbackTeams: Team[] = [
  { id: '1', name: 'Code Review Team', description: 'Specialized in reviewing PRs', members: 3, created: '2023-10-01', status: 'active' },
  { id: '2', name: 'Research Assistants', description: 'Gathers and summarizes info', members: 2, created: '2023-10-15', status: 'idle' },
];

const fetchTeams = async (): Promise<Team[]> => {
  const res = await fetch('/teams/export?format=json');
  if (!res.ok) {
    throw new Error(`Failed to load teams: ${res.status}`);
  }
  const data: Record<string, Record<string, unknown>> = await res.json();
  const arr: Team[] = [];
  if (Object.keys(data).length === 0) {
    return [];
  }
  for (const [slug, tObj] of Object.entries(data)) {
    arr.push({
      id: (tObj.id as string) || slug,
      name: (tObj.name as string) || slug,
      description: (tObj.description as string) || (tObj.desc as string) || '',
      members: (tObj.agent_count as number) || (Array.isArray(tObj.agents) ? tObj.agents.length : 0) || 1,
      created: tObj.created_at ? new Date(tObj.created_at as string).toLocaleDateString() : 'Unknown',
      status: 'idle',
      llm_profile: (tObj.llm_profile as string) || undefined,
    });
  }
  return arr;
};

export const TeamsPage = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formLlm, setFormLlm] = useState('');

  const { data: teams = fallbackTeams, isPending, isError } = useQuery({
    queryKey: ['teams'],
    queryFn: fetchTeams,
    retry: 1,
  });

  const createTeamMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const res = await fetch('/teams/', { method: 'POST', body: formData });
      if (!res.ok && res.status !== 200) {
        throw new Error('Create POST returned non-ok (but may have side-effected)');
      }
      return res;
    },
    onSuccess: (_, variables) => {
      setShowCreateModal(false);
      setSuccessMsg(`Team "${variables.get('team_name')}" created successfully.`);
      setFormName('');
      setFormDesc('');
      setFormLlm('');
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      setTimeout(() => setSuccessMsg(null), 5000);
    },
    onError: (e: Error) => {
      setError(`Create failed via form POST: ${e.message}.`);
    },
  });

  const deleteTeamMutation = useMutation({
    mutationFn: async (id: string | number) => {
      const fd = new FormData();
      fd.append('action', 'delete');
      fd.append('team_id', String(id));
      const res = await fetch('/teams/', { method: 'POST', body: fd });
      if (!res.ok && res.status !== 200) {
        throw new Error('Delete POST returned non-ok');
      }
      return id;
    },
    onSuccess: (id) => {
      setSuccessMsg(`Deleted ${id}. Registry updated.`);
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      setTimeout(() => setSuccessMsg(null), 3000);
    },
    onError: () => {
      setError('Delete failed (local UI may be stale; try refresh or server admin).');
    },
  });

  const filteredTeams = teams.filter(team =>
    team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    team.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDelete = (id: string | number) => {
    if (!window.confirm(`Delete team "${id}"? (calls backend)`)) return;
    setError(null);
    deleteTeamMutation.mutate(id);
  };

  const openCreate = () => {
    setFormName('');
    setFormDesc('');
    setFormLlm('');
    setShowCreateModal(true);
    setError(null);
  };

  const handleCreate = () => {
    if (!formName.trim()) {
      setError('Team name is required');
      return;
    }
    setError(null);
    const fd = new FormData();
    fd.append('team_name', formName.trim());
    if (formDesc.trim()) fd.append('description', formDesc.trim());
    if (formLlm.trim()) fd.append('llm_profile', formLlm.trim());
    createTeamMutation.mutate(fd);
  };

  const handleLaunch = (team: Team) => {
    const modelId = typeof team.id === 'string' ? team.id : team.name.toLowerCase().replace(/\s+/g, '-');
    setSuccessMsg(`Launch: use model="${modelId}" with /v1/chat/completions (stream=true supported in backend chat_views). See Settings for auth notes.`);
    setTimeout(() => setSuccessMsg(null), 6000);
  };

  const isActionLoading = createTeamMutation.isPending || deleteTeamMutation.isPending;

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
          <Button variant="primary" onClick={openCreate} disabled={isActionLoading}>
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </Button>
          <Button variant="outline" onClick={() => queryClient.invalidateQueries({ queryKey: ['teams'] })} disabled={isPending}>
            <Search className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      <div aria-live="polite" aria-atomic="true">
        {error && <Alert type="error" className="mb-4">{error}</Alert>}
        {isError && !error && <Alert type="warning" className="mb-4">Could not load teams. Using fallback or no data.</Alert>}
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
            <select className="select select-bordered w-full max-w-xs" onChange={() => { /* filter client-side for now */ }}>
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </Card>

      <div aria-busy={isPending} role={isPending ? 'status' : undefined}>
        {isPending && <div className="flex justify-center py-8"><LoadingSpinner /></div>}

        {/* Teams Grid */}
        {!isPending && filteredTeams.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredTeams.map((team) => (
              <Card key={team.id} bordered className="hover:shadow-lg transition-shadow">
                <div className="card-body">
                  <div className="flex justify-between items-start mb-2">
                    <Badge type={statusColors[team.status]}>
                      {team.status.charAt(0).toUpperCase() + team.status.slice(1)}
                    </Badge>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" className="btn-xs" title="Edit (demo)">
                        <Edit className="h-3 w-3" />
                      </Button>
                      <Button variant="ghost" size="sm" className="btn-xs" onClick={() => handleDelete(team.id)} disabled={isActionLoading}>
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
                    <Button variant="primary" size="sm" onClick={() => handleLaunch(team)} disabled={isActionLoading}>
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
        {!isPending && filteredTeams.length === 0 && (
          <Card bordered className="text-center py-12">
            <div className="mb-4">
              <Users className="h-16 w-16 mx-auto text-gray-400" />
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
      </div>

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
            <label className="label">
              <span className="label-text">Team Name *</span>
            </label>
            <input
              type="text"
              placeholder="e.g., code-review"
              className="input input-bordered w-full"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              disabled={isActionLoading}
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
              disabled={isActionLoading}
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
              disabled={isActionLoading}
            />
          </div>
        </div>

        <div className="modal-action flex gap-2 mt-4">
          <Button variant="outline" onClick={() => setShowCreateModal(false)} disabled={isActionLoading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleCreate} loading={isActionLoading} disabled={isActionLoading || !formName.trim()}>
            {isActionLoading ? 'Creating...' : 'Create Team'}
          </Button>
        </div>
        <div className="text-xs opacity-60 mt-2">Action uses available /teams/ endpoint (form POST). Refresh to see in other pages.</div>
      </Modal>

      {isActionLoading && <div className="fixed bottom-4 right-4"><LoadingSpinner /></div>}
    </div>
  );
};

export default TeamsPage;
