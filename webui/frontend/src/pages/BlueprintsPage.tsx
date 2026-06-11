import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Alert, SkeletonCard } from '../components/DaisyUI';
import { Book, Search, AlertCircle, Server } from 'lucide-react';
import { fetchBlueprints, type Blueprint } from '../lib/api';

const BlueprintsPage = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
  });

  const blueprints: Blueprint[] = data?.data ?? [];

  const filteredBlueprints = blueprints.filter((blueprint) => {
    const term = searchTerm.toLowerCase();
    return (
      blueprint.id.toLowerCase().includes(term) ||
      blueprint.name.toLowerCase().includes(term) ||
      blueprint.description.toLowerCase().includes(term)
    );
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Book className="h-8 w-8" />
          Blueprint Library
        </h1>
        <p className="text-base-content/70">Blueprints available on this server</p>
      </div>

      {/* Search */}
      <Card bordered className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
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
        </div>
      </Card>

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
            <span className="font-medium">Failed to load blueprints</span>
            <span className="text-sm">{error instanceof Error ? error.message : 'Unknown error'}</span>
            <div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Retry
              </Button>
            </div>
          </div>
        </Alert>
      )}

      {/* Blueprint grid */}
      {!isPending && !isError && filteredBlueprints.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBlueprints.map((blueprint) => (
            <div
              key={blueprint.id}
              className="card bg-base-100 border border-base-300 hover:shadow-md transition-shadow h-full"
            >
              <div className="card-body flex flex-col">
                {/* flex-wrap + break-words: long unbroken names (e.g.
                    WhiskeyTangoFoxtrotBlueprint) must not push the badge
                    outside the card / widen the page on small screens. */}
                <div className="flex flex-wrap justify-between items-start gap-2">
                  <h3 className="card-title text-base leading-snug min-w-0 break-words">{blueprint.name}</h3>
                  <span className="badge badge-neutral badge-sm font-mono shrink-0">
                    {blueprint.abbreviation || blueprint.id}
                  </span>
                </div>

                <p className="text-xs text-base-content/50 font-mono">{blueprint.id}</p>
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
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isPending && !isError && filteredBlueprints.length === 0 && (
        <Card bordered className="text-center py-12">
          <div className="mb-4">
            <Book className="h-16 w-16 mx-auto text-base-content/40" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No blueprints found</h3>
          <p className="text-base-content/70 mb-4">
            {searchTerm
              ? 'No blueprints match your search criteria'
              : 'No blueprints are registered on this server'}
          </p>
          {searchTerm && (
            <div>
              <Button variant="outline" onClick={() => setSearchTerm('')}>
                Reset Search
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default BlueprintsPage;
