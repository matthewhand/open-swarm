import { useState, useEffect } from 'react';
import { Button, Card, Alert, Badge, LoadingSpinner } from '../components/DaisyUI';
import { Book, Plus, Search, Eye, Play } from 'lucide-react';

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
  const [launchResult, setLaunchResult] = useState<string | null>(null);
  const [launchingId, setLaunchingId] = useState<string | null>(null);

  // Load real (or demo) blueprints from backend API
  useEffect(() => {
    const fetchBlueprints = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch('/v1/blueprints');
        if (res.ok) {
          const data = await res.json() as unknown;

          let list: Record<string, unknown>[] = [];
          if (Array.isArray(data)) {
            list = data as Record<string, unknown>[];
          } else if (data && typeof data === 'object') {
            const dataObj = data as Record<string, unknown>;
            if (Array.isArray(dataObj.data)) {
              list = dataObj.data as Record<string, unknown>[];
            } else if (Array.isArray(dataObj.blueprints)) {
              list = dataObj.blueprints as Record<string, unknown>[];
            }
          }

          setBlueprints(list.map((b) => ({
            id: String(b.id || b.name || Math.random()),
            name: (b.name as string) || (b.id as string) || 'unknown',
            description: (b.description as string) || (b.desc as string) || 'Blueprint for AI tasks',
            category: (b.category as string) || (b.tag as string) || 'General',
            version: (b.version as string) || '0.1',
            installed: !!b.installed,
            featured: !!b.featured,
          })));
        } else {
          throw new Error('API not available');
        }
      } catch (e: unknown) {
        setError('Using demo data (backend /v1/blueprints not reachable in this env)');
        setBlueprints([
          {id:'codey', name:'Codey', description:'Code generation & review assistant', category:'Development', version:'1.2', installed:true, featured:true},
          {id:'chatbot', name:'Chatbot', description:'General conversation agent', category:'General', version:'1.0'},
          {id:'geese', name:'Geese', description:'Collaborative writing team', category:'Writing', version:'0.9'},
        ]);
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

  const handleLaunch = async (bp: Blueprint) => {
    setLaunchResult(`Attempting launch of ${bp.name}...`);
    setLaunchingId(bp.id);
    try {
      // Example: could call a launch or chat endpoint
      await new Promise(r => setTimeout(r, 800));
      setLaunchResult(`Launched ${bp.name} (simulated via UI - real launch would use CLI or /v1/chat/completions)`);
    } catch (e: unknown) {
      setLaunchResult(`Launch request sent for ${bp.name}`);
    } finally {
      setLaunchingId(null);
      setTimeout(() => setLaunchResult(null), 4000);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Book className="h-8 w-8" />
          Blueprint Library
        </h1>
        <p className="text-gray-500">Discover, install, and manage agent blueprints.</p>
      </div>

      {error && <Alert type="warning" className="mb-4">{error}</Alert>}
      {launchResult && <Alert type="success" className="mb-4">{launchResult}</Alert>}

      {/* Controls */}
      <div className="flex flex-col md:flex-row justify-between gap-4 mb-6">
        <div className="flex flex-1 max-w-md gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search blueprints..."
              className="input input-bordered w-full pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button variant="outline">Filter</Button>
        </div>
        <Button variant="primary">
          <Plus className="h-4 w-4 mr-2" />
          Import Blueprint
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filtered.map(blueprint => (
            <Card key={blueprint.id} bordered className="h-full flex flex-col">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  <div className="text-2xl">{blueprint.featured ? '⭐' : '📦'}</div>
                  {blueprint.installed && <Badge type="success">Installed</Badge>}
                </div>

                <h3 className="card-title mb-2">{blueprint.name}</h3>
                <p className="text-sm text-gray-500 mb-4 flex-1">{blueprint.description}</p>

                <div className="text-xs mb-3">
                  <Badge type="info" size="sm">{blueprint.category || 'General'}</Badge>
                  {blueprint.version && <span className="ml-2">v{blueprint.version}</span>}
                </div>

                <div className="card-actions justify-end mt-auto">
                  <Button variant="outline" size="sm">
                    <Eye className="h-4 w-4 mr-1" />
                    Details
                  </Button>
                  <Button variant="primary" size="sm" onClick={() => handleLaunch(blueprint)} loading={launchingId === blueprint.id} disabled={launchingId !== null}>
                    <Play className="h-4 w-4 mr-1" />
                    Launch
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No blueprints found matching your search.
        </div>
      )}
    </div>
  );
}
