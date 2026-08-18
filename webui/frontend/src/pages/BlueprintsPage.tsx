import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, Alert, Badge, LoadingSpinner } from '../components/DaisyUI';
import { Book, Search, Eye, Play, ArchiveX } from 'lucide-react';

interface Blueprint {
  id: string;
  name: string;
  description?: string;
  category?: string;
  version?: string;
  installed?: boolean;
  featured?: boolean;
}

export default function BlueprintsPage() {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live list from /v1/blueprints — never invent demo rows on failure.
  useEffect(() => {
    const fetchBlueprints = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch('/v1/blueprints');
        if (res.ok) {
          const data = await res.json();
          const list = Array.isArray(data) ? data : (data.data || data.blueprints || []);
          setBlueprints(list.map((item: unknown) => {
            if (typeof item !== 'object' || item === null) {
              return {
                id: String(Math.random()),
                name: 'unknown',
                description: 'Blueprint for AI tasks',
                category: 'General',
                version: '0.1',
                installed: false,
                featured: false,
              };
            }
            const b = item as Record<string, unknown>;
            const bId = String(b.id || b.name || Math.random());

            return {
              id: bId,
              name: typeof b.name === 'string' ? b.name : (typeof b.id === 'string' ? b.id : 'unknown'),
              description: typeof b.description === 'string' ? b.description : (typeof b.desc === 'string' ? b.desc : 'Blueprint for AI tasks'),
              category: typeof b.category === 'string' ? b.category : (typeof b.tag === 'string' ? b.tag : 'General'),
              version: typeof b.version === 'string' ? b.version : '0.1',
              installed: !!b.installed,
              featured: !!b.featured,
            };
          }));
        } else {
          throw new Error(`HTTP ${res.status}`);
        }
      } catch (e) {
        const detail = e instanceof Error ? e.message : String(e);
        setError(
          `Could not load blueprints from /v1/blueprints (${detail}). Open the Django library or check that the API is running.`,
        );
        setBlueprints([]);
      } finally {
        setLoading(false);
      }
    };
    fetchBlueprints();
  }, []);

  const filtered = blueprints.filter(b =>
    b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (b.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Book className="h-8 w-8" aria-hidden="true" />
          Blueprint Library
        </h1>
        <p className="text-base-content/70">Browse discoverable blueprints from the live API</p>
      </div>

      <Alert type="info" role="status" className="mb-4">
        <span className="text-sm">
          Prefer the full library at{' '}
          <a className="link font-semibold" href="/blueprint-library/">
            /blueprint-library/
          </a>
          . Bare <code>/blueprints</code> redirects there when served by Django. Launch opens SPA chat with the blueprint preselected (session login required).
        </span>
      </Alert>

      {error && (
        <Alert type="warning" role="alert" className="mb-4">
          <div className="space-y-2 text-sm">
            <p>{error}</p>
            <a className="link font-semibold" href="/blueprint-library/">
              Open /blueprint-library/
            </a>
          </div>
        </Alert>
      )}

      <div className="mb-4 flex gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="h-4 w-4 absolute left-3 top-3 text-base-content/40" aria-hidden="true" />
          <label htmlFor="blueprints-search" className="sr-only">
            Search blueprints
          </label>
          <input
            id="blueprints-search"
            type="search"
            placeholder="Search blueprints..."
            className="input input-bordered pl-10 w-full"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12" aria-live="polite" aria-busy="true" role="status">
          <LoadingSpinner />
          <span className="sr-only">Loading blueprints</span>
        </div>
      ) : filtered.length === 0 ? (
        <Card bordered className="text-center py-12" role="status">
          <div className="mb-4">
            <ArchiveX className="h-16 w-16 mx-auto text-base-content/40" aria-hidden="true" />
          </div>
          <h3 className="text-xl font-semibold mb-2">
            {error ? 'Blueprints unavailable' : 'No blueprints found'}
          </h3>
          <p className="text-base-content/70 mb-4">
            {searchTerm
              ? 'No blueprints match your search criteria.'
              : error
                ? 'Nothing listed until /v1/blueprints responds.'
                : 'No blueprints available from the API yet.'}
          </p>
          <a className="btn btn-primary btn-sm" href="/blueprint-library/">
            Open Django library
          </a>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((blueprint) => (
            <Card key={blueprint.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  {blueprint.installed && <Badge type="success" size="sm">Installed</Badge>}
                  {blueprint.featured && <Badge type="warning" size="sm">Featured</Badge>}
                </div>

                <h3 className="card-title mb-2">{blueprint.name}</h3>
                <p className="text-sm text-base-content/70 mb-4">{blueprint.description}</p>

                <div className="text-xs mb-3">
                  <Badge type="info" size="sm">{blueprint.category || 'General'}</Badge>
                  {blueprint.version && <span className="ml-2">v{blueprint.version}</span>}
                </div>

                <div className="card-actions justify-end">
                  <a
                    className="btn btn-outline btn-sm"
                    href="/blueprint-library/"
                    aria-label={`Details for ${blueprint.name} in Django library`}
                  >
                    <Eye className="h-4 w-4 mr-1" aria-hidden="true" />
                    Details
                  </a>
                  <Link
                    className="btn btn-primary btn-sm"
                    to={`/chat?blueprint=${encodeURIComponent(blueprint.id)}`}
                    aria-label={`Open chat with ${blueprint.name}`}
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

      <div className="mt-6 text-xs opacity-60">
        Data source: /v1/blueprints. Use swarm-cli or /teams/launch/ for install and team launch.
      </div>
    </div>
  );
}
