import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
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

const fetchBlueprints = async (): Promise<Blueprint[]> => {
  const res = await fetch('/v1/blueprints');
  if (!res.ok) {
    throw new Error('API not available');
  }
  const data: { data?: Record<string, unknown>[]; blueprints?: Record<string, unknown>[] } | Record<string, unknown>[] = await res.json();
  const list = Array.isArray(data) ? data : (data.data || data.blueprints || []);

  return list.map((b: Record<string, unknown>) => ({
    id: String(b.id || b.name || Math.random()),
    name: (b.name as string) || (b.id as string) || 'unknown',
    description: (b.description as string) || (b.desc as string) || 'Blueprint for AI tasks',
    category: (b.category as string) || (b.tag as string) || 'General',
    version: (b.version as string) || '0.1',
    installed: !!b.installed,
    featured: !!b.featured,
  }));
};

const fallbackBlueprints: Blueprint[] = [
  {id:'codey', name:'Codey', description:'Code generation & review assistant', category:'Development', version:'1.2', installed:true, featured:true},
  {id:'chatbot', name:'Chatbot', description:'General conversation agent', category:'General', version:'1.0'},
  {id:'geese', name:'Geese', description:'Collaborative writing team', category:'Writing', version:'0.9'},
];

export default function BlueprintsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [launchResult, setLaunchResult] = useState<string | null>(null);

  const { data: blueprints = fallbackBlueprints, isPending, isError } = useQuery({
    queryKey: ['blueprints'],
    queryFn: fetchBlueprints,
    retry: 1,
  });

  const launchMutation = useMutation({
    mutationFn: async (bp: Blueprint) => {
      // Simulated launch API call
      await new Promise(r => setTimeout(r, 800));
      return bp;
    },
    onMutate: (bp) => {
      setLaunchResult(`Attempting launch of ${bp.name}...`);
    },
    onSuccess: (bp) => {
      setLaunchResult(`Launched ${bp.name} (simulated via UI - real launch would use CLI or /v1/chat/completions)`);
      setTimeout(() => setLaunchResult(null), 4000);
    },
    onError: (_, bp) => {
       setLaunchResult(`Launch request failed for ${bp.name}`);
       setTimeout(() => setLaunchResult(null), 4000);
    }
  });


  const filtered = blueprints.filter(b =>
    b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (b.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleLaunch = (bp: Blueprint) => {
    launchMutation.mutate(bp);
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

      <div aria-live="polite" aria-atomic="true">
        {isError && <Alert type="warning" className="mb-4">Using demo data (backend /v1/blueprints not reachable in this env)</Alert>}
        {launchResult && <Alert type={launchMutation.isError ? "error" : "success"} className="mb-4">{launchResult}</Alert>}
      </div>

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

      <div aria-busy={isPending} role={isPending ? "status" : undefined}>
        {isPending ? (
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
                    <Button variant="primary" size="sm" onClick={() => handleLaunch(blueprint)} disabled={launchMutation.isPending}>
                      <Play className="h-4 w-4 mr-1" />
                      Launch
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 text-xs opacity-60">
        Data source: /v1/blueprints (or demo). Use swarm-cli for full install/launch.
      </div>
    </div>
  );
}
