import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmModal,
  Input,
  SkeletonCard,
  Textarea,
  ToastProvider,
  useToast,
} from '../components/DaisyUI';
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Plus,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react';
import {
  createCustomBlueprint,
  deleteCustomBlueprint,
  fetchCustomBlueprints,
  generateAgentCode,
  validateAgentCode,
  type CodeValidationResult,
  type CustomBlueprint,
} from '../lib/api';

/**
 * Agent creator page.
 *
 * - Generate/validate call the real Django endpoints
 *   (/agent-creator/generate/ and /agent-creator/validate/,
 *   swarm/views/agent_creator_views.py); api.ts primes the CSRF cookie first.
 * - Save posts to /v1/blueprints/custom/ rather than /agent-creator/save/:
 *   the latter writes loose files under user_blueprints/ with no list/delete
 *   API, while the custom-blueprint library gives this page a single store
 *   for save, list and delete. Nothing shown here is fabricated client-side.
 */
const AgentCreatorPageContent = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  // Spec form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [personality, setPersonality] = useState('');
  const [expertise, setExpertise] = useState('');
  const [communicationStyle, setCommunicationStyle] = useState('');

  // Code editor + last validation report
  const [code, setCode] = useState('');
  const [validation, setValidation] = useState<CodeValidationResult | null>(null);

  const [blueprintToDelete, setBlueprintToDelete] = useState<CustomBlueprint | null>(null);

  const customQuery = useQuery({
    queryKey: ['custom-blueprints'],
    queryFn: fetchCustomBlueprints,
  });
  const customBlueprints: CustomBlueprint[] = customQuery.data?.data ?? [];

  const generateMutation = useMutation({
    mutationFn: generateAgentCode,
    onSuccess: (res) => {
      setCode(res.code);
      setValidation(res.validation);
      toast.success('Code generated', 'Review the code below, then save.');
    },
    onError: (err) => {
      toast.error(
        'Generation failed',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
  });

  const validateMutation = useMutation({
    mutationFn: validateAgentCode,
    onSuccess: (res) => {
      setValidation(res.validation);
      if (res.validation.valid) {
        toast.success('Validation passed', 'The blueprint code is valid.');
      } else {
        toast.warning('Validation failed', 'See the issues listed below.');
      }
    },
    onError: (err) => {
      toast.error(
        'Validation request failed',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
  });

  const saveMutation = useMutation({
    mutationFn: createCustomBlueprint,
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['custom-blueprints'] });
      toast.success('Agent saved', `Saved as custom blueprint "${saved.id}".`);
    },
    onError: (err) => {
      toast.error(
        'Save failed',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCustomBlueprint,
    onSuccess: (_data, blueprintId) => {
      queryClient.invalidateQueries({ queryKey: ['custom-blueprints'] });
      toast.success('Blueprint deleted', `"${blueprintId}" was removed.`);
    },
    onError: (err) => {
      toast.error(
        'Delete failed',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
    onSettled: () => setBlueprintToDelete(null),
  });

  const specComplete =
    name.trim().length > 0 &&
    description.trim().length > 0 &&
    instructions.trim().length > 0;

  const handleGenerate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!specComplete || generateMutation.isPending) return;
    generateMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      instructions: instructions.trim(),
      ...(personality.trim() ? { personality: personality.trim() } : {}),
      ...(expertise.trim()
        ? {
            expertise: expertise
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean),
          }
        : {}),
      ...(communicationStyle.trim()
        ? { communication_style: communicationStyle.trim() }
        : {}),
    });
  };

  const handleValidate = () => {
    if (!code.trim() || validateMutation.isPending) return;
    validateMutation.mutate(code);
  };

  const handleSave = () => {
    if (!specComplete || !code.trim() || saveMutation.isPending) return;
    saveMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      code,
      tags: ['custom', 'agent-creator'],
    });
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Wand2 className="h-8 w-8" />
          Agent Creator
        </h1>
        <p className="text-base-content/70 mt-1">
          Generate a blueprint from a persona spec, validate the Python code
          server-side, and save it to the custom blueprint library
          (/v1/blueprints/custom/).
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        {/* Spec form */}
        <Card bordered>
          <h2 className="card-title flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Agent specification
          </h2>
          <form onSubmit={handleGenerate} className="space-y-3 mt-2">
            <Input
              label="Name *"
              placeholder="e.g. Research Assistant"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={64}
            />
            <Input
              label="Description *"
              placeholder="What does this agent do?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
            <Textarea
              label="Instructions *"
              placeholder="System-prompt style instructions for the agent…"
              rows={4}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              required
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Input
                label="Personality (optional)"
                placeholder="helpful and professional"
                value={personality}
                onChange={(e) => setPersonality(e.target.value)}
              />
              <Input
                label="Communication style (optional)"
                placeholder="clear and concise"
                value={communicationStyle}
                onChange={(e) => setCommunicationStyle(e.target.value)}
              />
            </div>
            <Input
              label="Expertise (optional, comma-separated)"
              placeholder="coding, research, writing"
              value={expertise}
              onChange={(e) => setExpertise(e.target.value)}
            />
            <div className="card-actions justify-end pt-2">
              <Button
                type="submit"
                variant="primary"
                loading={generateMutation.isPending}
                disabled={!specComplete || generateMutation.isPending}
              >
                <Wand2 className="h-4 w-4 mr-2" />
                Generate code
              </Button>
            </div>
          </form>
        </Card>

        {/* Code editor + validation */}
        <Card bordered>
          <h2 className="card-title flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            Blueprint code
          </h2>
          <p className="text-sm text-base-content/70">
            Generated code lands here; you can also paste or edit code by hand
            before validating and saving.
          </p>
          <Textarea
            aria-label="Blueprint Python code"
            className="font-mono text-xs leading-snug min-h-72"
            rows={18}
            placeholder="# Generate code from a spec, or paste blueprint Python here…"
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              // Edits invalidate the previous validation report.
              setValidation(null);
            }}
            spellCheck={false}
          />

          {validation && (
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2">
                {validation.valid ? (
                  <Badge type="success">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    valid
                  </Badge>
                ) : (
                  <Badge type="error">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    invalid
                  </Badge>
                )}
                <Badge type={validation.syntax_valid ? 'success' : 'error'} size="sm">
                  syntax
                </Badge>
                <Badge type={validation.structure_valid ? 'success' : 'error'} size="sm">
                  structure
                </Badge>
                <Badge type={validation.lint_clean ? 'success' : 'warning'} size="sm">
                  lint
                </Badge>
              </div>
              {validation.errors.length > 0 && (
                <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
                  <ul className="list-disc list-inside text-sm">
                    {validation.errors.map((err) => (
                      <li key={err}>{err}</li>
                    ))}
                  </ul>
                </Alert>
              )}
              {validation.warnings.length > 0 && (
                <Alert type="warning" icon={<AlertCircle className="h-5 w-5" />}>
                  <ul className="list-disc list-inside text-sm">
                    {validation.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </Alert>
              )}
            </div>
          )}

          <div className="card-actions justify-end pt-2">
            <Button
              type="button"
              variant="outline"
              loading={validateMutation.isPending}
              disabled={!code.trim() || validateMutation.isPending}
              onClick={handleValidate}
            >
              <ShieldCheck className="h-4 w-4 mr-2" />
              Validate
            </Button>
            <Button
              type="button"
              variant="primary"
              loading={saveMutation.isPending}
              disabled={!specComplete || !code.trim() || saveMutation.isPending}
              onClick={handleSave}
              title={
                specComplete
                  ? undefined
                  : 'Fill in name, description and instructions first'
              }
            >
              <Save className="h-4 w-4 mr-2" />
              Save to library
            </Button>
          </div>
        </Card>
      </div>

      {/* Existing custom blueprints */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2 mb-4">
          <Bot className="h-6 w-6" />
          Custom blueprints
        </h2>

        {customQuery.isPending && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        )}

        {customQuery.isError && (
          <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
            <div className="flex flex-col gap-2">
              <span className="font-medium">Failed to load custom blueprints</span>
              <span className="text-sm">
                {customQuery.error instanceof Error
                  ? customQuery.error.message
                  : 'Unknown error'}
              </span>
              <div>
                <Button variant="outline" size="sm" onClick={() => customQuery.refetch()}>
                  Retry
                </Button>
              </div>
            </div>
          </Alert>
        )}

        {!customQuery.isPending && !customQuery.isError && customBlueprints.length === 0 && (
          <Card bordered className="text-center py-10">
            <Bot className="h-14 w-14 mx-auto text-base-content/60 mb-3" />
            <h3 className="text-lg font-semibold mb-1">No custom blueprints yet</h3>
            <p className="text-base-content/70 text-sm">
              Agents saved from this page appear here (stored in the server's
              blueprint library).
            </p>
          </Card>
        )}

        {!customQuery.isPending && !customQuery.isError && customBlueprints.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {customBlueprints.map((blueprint) => (
              <Card key={blueprint.id} bordered className="hover:shadow-lg transition-shadow">
                <div className="card-body">
                  <div className="flex items-start gap-3 mb-2">
                    <div className="flex-none h-10 w-10 rounded-full bg-base-200 border border-base-300 flex items-center justify-center text-base-content/60">
                      <Wand2 className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="card-title font-mono text-base truncate" title={blueprint.id}>
                        {blueprint.id}
                      </h3>
                      <span className="text-xs text-base-content/60">{blueprint.category}</span>
                    </div>
                    <Badge type="info" size="sm">Custom</Badge>
                  </div>
                  <p className="text-sm text-base-content/70 mb-2">
                    {blueprint.description || 'No description provided.'}
                  </p>
                  {blueprint.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {blueprint.tags.map((tag) => (
                        <Badge key={tag} type="ghost" size="sm">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <div className="card-actions justify-end">
                    <Button
                      variant="outline"
                      color="error"
                      size="sm"
                      onClick={() => setBlueprintToDelete(blueprint)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="h-4 w-4 mr-1" />
                      Delete
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
            {/* Ghost card: fills out the grid and invites creating another agent */}
            <button
              type="button"
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="card border-2 border-dashed border-base-300 bg-transparent text-base-content/60 hover:border-primary hover:text-primary transition-colors flex items-center justify-center min-h-[180px]"
            >
              <div className="text-center">
                <Plus className="h-8 w-8 mx-auto mb-2" />
                <span className="font-medium">Create a new agent</span>
              </div>
            </button>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={blueprintToDelete !== null}
        onClose={() => setBlueprintToDelete(null)}
        onConfirm={() => {
          if (blueprintToDelete && !deleteMutation.isPending) {
            deleteMutation.mutate(blueprintToDelete.id);
          }
        }}
        title="Delete Custom Blueprint"
        confirmText="Delete"
        confirmVariant="error"
      >
        <p>
          Delete custom blueprint{' '}
          <span className="font-mono font-semibold">{blueprintToDelete?.id}</span>?
          This removes it from the server's blueprint library.
        </p>
      </ConfirmModal>
    </div>
  );
};

const AgentCreatorPage = () => (
  <ToastProvider>
    <AgentCreatorPageContent />
  </ToastProvider>
);

export default AgentCreatorPage;
