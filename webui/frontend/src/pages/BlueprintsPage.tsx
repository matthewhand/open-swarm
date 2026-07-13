import React, { useState, useEffect } from 'react';
import { Button, Card, Alert, Badge, LoadingSpinner } from '../components/DaisyUI';
import { Book, Search, Eye, Play } from 'lucide-react';

interface Blueprint {
  id: string;
  name: string;
  description?: string;
  category?: string;
  version?: string;
  installed?: boolean;
  featured?: boolean;
}

interface BlueprintApiData {
  id?: string;
  name?: string;
  description?: string;
  desc?: string;
  category?: string;
  tag?: string;
  version?: string;
  installed?: boolean;
  featured?: boolean;
  [key: string]: unknown;
}

interface BlueprintApiResponse {
  data?: BlueprintApiData[];
  blueprints?: BlueprintApiData[];
  [key: string]: unknown;
}

export default function BlueprintsPage() {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [launchResult, setLaunchResult] = useState<string | null>(null);

  // Load real (or demo) blueprints from backend API
  useEffect(() => {
    const fetchBlueprints = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch('/v1/blueprints');
        if (res.ok) {
          const data = await res.json() as BlueprintApiResponse | BlueprintApiData[];
          const list = Array.isArray(data) ? data : (data.data || data.blueprints || []);
          setBlueprints(list.map((b: BlueprintApiData) => ({
            id: String(b.id || b.name || Math.random()),
            name: b.name || b.id || 'unknown',
            description: b.description || b.desc || 'Blueprint for AI tasks',
            category: b.category || b.tag || 'General',
            version: b.version || '0.1',
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
    try {
      // Example: could call a launch or chat endpoint
      await new Promise(r => setTimeout(r, 800));
      setLaunchResult(`Launched ${bp.name} (simulated via UI - real launch would use CLI or /v1/chat/completions)`);
    } catch {
      setLaunchResult(`Launch request sent for ${bp.name}`);
    }
    setTimeout(() => setLaunchResult(null), 4000);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Book className="h-8 w-8" />
          Blueprint Library
        </h1>
        <p className="text-gray-500">Browse and install AI blueprints for your projects (live data preferred)</p>
      </div>

      {error && <Alert type="warning">{error}</Alert>}
      {launchResult && <Alert type="success" className="mb-4">{launchResult}</Alert>}

      <div className="mb-4 flex gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            placeholder="Search blueprints..."
            className="input input-bordered pl-10 w-full"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
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
                <p className="text-sm text-gray-500 mb-4">{blueprint.description}</p>

                <div className="text-xs mb-3">
                  <Badge type="info" size="sm">{blueprint.category || 'General'}</Badge>
                  {blueprint.version && <span className="ml-2">v{blueprint.version}</span>}
                </div>

                <div className="card-actions justify-end">
                  <Button variant="outline" size="sm">
                    <Eye className="h-4 w-4 mr-1" />
                    Details
                  </Button>
                  <Button variant="primary" size="sm" onClick={() => handleLaunch(blueprint)}>
                    <Play className="h-4 w-4 mr-1" />
                    Launch
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-6 text-xs opacity-60">
        Data source: /v1/blueprints (or demo). Use swarm-cli for full install/launch.
      </div>
    </div>
  );
}
