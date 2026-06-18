import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Alert, SkeletonCard, ToastProvider, useToast } from '../components/DaisyUI';
import { Book, Search, AlertCircle, Server, BookmarkPlus, BookmarkCheck } from 'lucide-react';
import {
  addToLibrary,
  fetchBlueprints,
  fetchLibrary,
  removeFromLibrary,
  type Blueprint,
} from '../lib/api';

/**
 * Blueprint library page.
 *
 * The catalog comes from /v1/blueprints/; the per-deployment "My Library"
 * (install) state comes from /v1/library/ (swarm/views/library_api.py), the
 * JSON counterpart to the server-rendered /blueprint-library/ pages.
 */
const BlueprintsPageContent = () => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const [searchTerm, setSearchTerm] = useState('');
  const [libraryOnly, setLibraryOnly] = useState(false);

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  });

  const libraryQuery = useQuery({
    queryKey: ['library'],
    queryFn: fetchLibrary,
  });

  const libraryIds = new Set(
    (libraryQuery.data?.data ?? []).map((entry) => entry.id),
  );

  const addMutation = useMutation({
    mutationFn: addToLibrary,
    onSuccess: (entry) => {
      queryClient.invalidateQueries({ queryKey: ['library'] });
      toast.success('Added to library', `"${entry.name}" is now in your library.`);
    },
    onError: (err) => {
      toast.error(
        'Failed to add blueprint',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeFromLibrary,
    onSuccess: (_data, name) => {
      queryClient.invalidateQueries({ queryKey: ['library'] });
      toast.success('Removed from library', `"${name}" was removed from your library.`);
    },
    onError: (err) => {
      toast.error(
        'Failed to remove blueprint',
        err instanceof Error ? err.message : 'Unknown error',
      );
    },
  });

  const blueprints: Blueprint[] = data?.data ?? [];

  const filteredBlueprints = blueprints.filter((blueprint) => {
    if (libraryOnly && !libraryIds.has(blueprint.id)) {
      return false;
    }
    const term = searchTerm.toLowerCase();
    return (
      blueprint.id.toLowerCase().includes(term) ||
      blueprint.name.toLowerCase().includes(term) ||
      blueprint.description.toLowerCase().includes(term)
    );
  });

  const isMutating = (id: string) =>
    (addMutation.isPending && addMutation.variables === id) ||
    (removeMutation.isPending && removeMutation.variables === id);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Book className="h-8 w-8" />
          Blueprint Library
        </h1>
        <p className="text-base-content/70">Blueprints available on this server</p>
      </div>

      {/* Search + library filter */}
      <Card bordered className="mb-6">
        <div className="flex flex-col md:flex-row gap-4 md:items-end">
          <div className="flex-1">
            <label className="label">
              <span className="label-text">Search Blueprints</span>
            </label>
            <div className="join w-full">
              <input
                type="text"
                placeholder="Search by name or description..."
                className="input input-bordered join-item w-full"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <button className="btn join-item" aria-label="Search">
                <Search className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="form-control pb-1">
            <label className="label cursor-pointer gap-3">
              <span className="label-text flex items-center gap-1">
                <BookmarkCheck className="h-4 w-4" />
                My Library only
                {libraryQuery.isSuccess && <span>({libraryIds.size})</span>}
              </span>
              <input
                type="checkbox"
                className="toggle toggle-primary"
                checked={libraryOnly}
                onChange={(e) => setLibraryOnly(e.target.checked)}
                disabled={libraryQuery.isError}
                aria-label="Show only blueprints in my library"
              />
            </label>
          </div>
        </div>
        {libraryQuery.isError && (
          <p className="text-xs text-warning mt-2">
            Could not load your library state; add/remove is unavailable.
          </p>
        )}
      </Card>

      {/* Loading state */}
      {isPending && (
        <div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          aria-busy="true"
          aria-live="polite"
        >
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div aria-live="assertive" role="alert">
          <Alert type="error" icon={<AlertCircle className="h-5 w-5" />}>
            <div className="flex flex-col gap-2">
              <span className="font-medium">Failed to load blueprints</span>
              <span className="text-sm">{error instanceof Error ? error.message : 'Unknown error'}</span>
              <div>
                <Button variant="outline" size="sm" onClick={() => refetch()}>
                  Retry
                </Button>
              </div>
            </div>
          </Alert>
        </div>
      )}

      {/* Blueprint grid */}
      {!isPending && !isError && filteredBlueprints.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBlueprints.map((blueprint) => {
            const inLibrary = libraryIds.has(blueprint.id);
            return (
              <div
                key={blueprint.id}
                className="card bg-base-100 border border-base-300 hover:shadow-md transition-shadow h-full"
              >
                <div className="card-body flex flex-col">
                  {/* flex-wrap + break-words: long unbroken names (e.g.
                      WhiskeyTangoFoxtrotBlueprint) must not push the badge
                      outside the card / widen the page on small screens. */}
                  <div className="flex flex-wrap justify-between items-start gap-2">
                    <h2 className="card-title text-base leading-snug min-w-0 break-words">{blueprint.name}</h2>
                    <span className="badge badge-neutral badge-sm font-mono shrink-0">
                      {blueprint.abbreviation || blueprint.id}
                    </span>
                  </div>

                  <p className="text-xs text-base-content/70 font-mono">{blueprint.id}</p>
                  <p
                    className="text-sm text-base-content/70 line-clamp-3"
                    title={blueprint.description}
                  >
                    {blueprint.description || 'No description provided.'}
                  </p>

                  <div className="mt-auto pt-3 space-y-2">
                    {blueprint.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {blueprint.tags.map((tag) => (
                          <span key={tag} className="badge badge-ghost badge-sm">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}

                    {blueprint.required_mcp_servers.length > 0 && (
                      <div className="border-t border-base-300 pt-2 text-sm">
                        <span className="flex items-center gap-1 text-xs font-medium text-base-content/60 uppercase tracking-wide">
                          <Server className="h-3 w-3" />
                          Required MCP servers
                        </span>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {blueprint.required_mcp_servers.map((server) => (
                            <span key={server} className="badge badge-outline badge-sm font-mono">
                              {server}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="card-actions justify-end border-t border-base-300 pt-2">
                      {inLibrary ? (
                        <Button
                          variant="outline"
                          color="success"
                          size="sm"
                          loading={isMutating(blueprint.id)}
                          disabled={isMutating(blueprint.id)}
                          onClick={() => removeMutation.mutate(blueprint.id)}
                          title="In your library — click to remove"
                          aria-label={`Remove ${blueprint.name} from library`}
                        >
                          <BookmarkCheck className="h-4 w-4 mr-1" />
                          In Library
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          loading={isMutating(blueprint.id)}
                          disabled={isMutating(blueprint.id) || libraryQuery.isError}
                          onClick={() => addMutation.mutate(blueprint.id)}
                          aria-label={`Add ${blueprint.name} to library`}
                        >
                          <BookmarkPlus className="h-4 w-4 mr-1" />
                          Add to Library
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty state */}
      {!isPending && !isError && filteredBlueprints.length === 0 && (
        <Card bordered className="text-center py-12" role="status" aria-live="polite">
          <div className="mb-4">
            <Book className="h-16 w-16 mx-auto text-base-content/70" />
          </div>
          <h2 className="text-xl font-semibold mb-2">No blueprints found</h2>
          <p className="text-base-content/70 mb-4">
            {searchTerm || libraryOnly
              ? 'No blueprints match your search criteria'
              : 'No blueprints are registered on this server'}
          </p>
          {(searchTerm || libraryOnly) && (
            <div className="flex justify-center gap-2">
              {searchTerm && (
                <Button variant="outline" onClick={() => setSearchTerm('')}>
                  Reset Search
                </Button>
              )}
              {libraryOnly && (
                <Button variant="outline" onClick={() => setLibraryOnly(false)}>
                  Show All Blueprints
                </Button>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

/**
 * The app shell does not mount a ToastProvider, so provide one locally for
 * add/remove feedback (same pattern as TeamsPage).
 */
const BlueprintsPage = () => (
  <ToastProvider>
    <BlueprintsPageContent />
  </ToastProvider>
);

export default BlueprintsPage;
