import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmModal,
  Input,
  Modal,
  SkeletonCard,
  ToastProvider,
  useToast,
} from '../components/DaisyUI';
import { AlertCircle, Plus, Rocket, Trash2, Users } from 'lucide-react';
import { createTeam, deleteTeam, fetchTeams, type Team } from '../lib/api';

/**
 * Teams page.
 *
 * Wired to the JSON Teams API (/v1/teams/, see swarm/views/teams_api.py),
 * which is backed by the same dynamic-team registry as the server-rendered
 * /teams/ admin page. All data shown here comes from the backend; nothing is
 * fabricated client-side.
 */
const TeamsPageContent = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const navigate = useNavigate();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [teamToDelete, setTeamToDelete] = useState<Team | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [llmProfile, setLlmProfile] = useState('');

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['teams'],
    queryFn: fetchTeams,
  });

  const teams: Team[] = data?.data ?? [];

  const resetForm = () => {
    setName('');
    setDescription('');
    setLlmProfile('');
  };

  const createMutation = useMutation({
    mutationFn: createTeam,
    onSuccess: (team) => {
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      setIsCreateOpen(false);
      resetForm();
      toast.success('Team created', `Team "${team.id}" was registered.`);
    },
    onError: (err) => {
      toast.error(
        'Failed to create team',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTeam,
    onSuccess: (_data, teamId) => {
      queryClient.invalidateQueries({ queryKey: ['teams'] });
      toast.success('Team deleted', `Team "${teamId}" was removed.`);
    },
    onError: (err) => {
      toast.error(
        'Failed to delete team',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
    onSettled: () => {
      setTeamToDelete(null);
    },
  });

  const handleCreateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || createMutation.isPending) return;
    createMutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      llm_profile: llmProfile.trim() || undefined,
    });
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Users className="h-8 w-8" />
            Team Management
          </h1>
          <p className="text-gray-500 mt-1">
            Create and manage dynamic AI teams (served by /v1/teams/)
          </p>
        </div>
        <div>
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-5 w-5 mr-2" />
            New Team
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isPending && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Error state */}
      {isError && (
        <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
          <div className="flex flex-col gap-2">
            <span className="font-medium">Failed to load teams</span>
            <span className="text-sm">
              {error instanceof Error ? error.message : 'Unknown error'}
            </span>
            <div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          </div>
        </Alert>
      )}

      {/* Team grid */}
      {!isPending && !isError && teams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams.map((team) => (
            <Card key={team.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start gap-2 mb-2">
                  <h3 className="card-title font-mono text-lg">{team.id}</h3>
                  <Badge type="info" size="sm">
                    {team.llm_profile}
                  </Badge>
                </div>
                <p className="text-sm text-gray-500 mb-4 whitespace-pre-line">
                  {team.description || 'No description provided.'}
                </p>
                <div className="card-actions justify-end">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() =>
                      navigate(`/chat?blueprint=${encodeURIComponent(team.id)}`)
                    }
                  >
                    <Rocket className="h-4 w-4 mr-1" />
                    Launch
                  </Button>
                  <Button
                    variant="outline"
                    color="error"
                    size="sm"
                    onClick={() => setTeamToDelete(team)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isPending && !isError && teams.length === 0 && (
        <Card bordered className="text-center py-12">
          <div className="mb-4">
            <Users className="h-16 w-16 mx-auto text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No teams yet</h3>
          <p className="text-gray-500 mb-4">
            No dynamic teams are registered on this server.
          </p>
          <div>
            <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
              <Plus className="h-5 w-5 mr-2" />
              Create your first team
            </Button>
          </div>
        </Card>
      )}

      {/* Create team modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Team"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <Input
            label="Team name"
            placeholder="e.g. Research Team"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={64}
          />
          <Input
            label="Description (optional)"
            placeholder="What does this team do?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Input
            label="LLM profile (optional)"
            placeholder="default"
            value={llmProfile}
            onChange={(e) => setLlmProfile(e.target.value)}
          />
          <p className="text-xs text-gray-400">
            The name is slugified server-side (lowercase letters, numbers and
            dashes) and exposed as a model id via /v1/models.
          </p>
          <div className="modal-action flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsCreateOpen(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={createMutation.isPending}
              disabled={!name.trim() || createMutation.isPending}
            >
              Create
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete confirmation modal */}
      <ConfirmModal
        isOpen={teamToDelete !== null}
        onClose={() => setTeamToDelete(null)}
        onConfirm={() => {
          if (teamToDelete && !deleteMutation.isPending) {
            deleteMutation.mutate(teamToDelete.id);
          }
        }}
        title="Delete Team"
        confirmText="Delete"
        confirmVariant="error"
      >
        <p>
          Delete team{' '}
          <span className="font-mono font-semibold">{teamToDelete?.id}</span>?
          This removes it from the registry and from /v1/models.
        </p>
      </ConfirmModal>
    </div>
  );
};

/**
 * The app shell does not mount a ToastProvider, so provide one locally for
 * create/delete feedback.
 */
const TeamsPage = () => (
  <ToastProvider>
    <TeamsPageContent />
  </ToastProvider>
);

export default TeamsPage;
