import React, { useState, useEffect } from 'react';
import { Button, Alert, Badge, LoadingSpinner } from '../components/DaisyUI';
import { Book, Plus, Search, Star, Download, Eye, Play } from 'lucide-react';

interface Blueprint {
  id: string;
  name: string;
  description?: string;
  category?: string;
  version?: string;
  installed?: boolean;
  featured?: boolean;
  popularity?: number;
}

export default function BlueprintsPage() {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
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
          const data = await res.json();
          const list = Array.isArray(data) ? data : (data.data || data.blueprints || []);
          setBlueprints(list.map((b: any) => ({
            id: String(b.id || b.name || Math.random()),
            name: b.name || b.id || 'unknown',
            description: b.description || b.desc || 'Blueprint for AI tasks',
            category: b.category || b.tag || 'General',
            version: b.version || '0.1',
            installed: !!b.installed,
            featured: !!b.featured,
            popularity: b.popularity || 0,
          })));
        } else {
          throw new Error('API not available');
        }
      } catch (e) {
        setError('Using demo data (backend /v1/blueprints not reachable in this env)');
        setBlueprints([
          {id:'codey', name:'Codey', description:'Code generation & review assistant', category:'Development', version:'1.2', installed:true, featured:true, popularity: 95},
          {id:'chatbot', name:'Chatbot', description:'General conversation agent', category:'General', version:'1.0', popularity: 80},
          {id:'geese', name:'Geese', description:'Collaborative writing team', category:'Writing', version:'0.9', popularity: 75},
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchBlueprints();
  }, []);

  const categories = ['all', ...Array.from(new Set(blueprints.map(b => b.category).filter(Boolean)))];

  const filteredBlueprints = blueprints.filter(bp =>
    bp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (bp.description || '').toLowerCase().includes(searchTerm.toLowerCase())
  ).filter(bp => categoryFilter === 'all' || bp.category === categoryFilter);

  const handleLaunch = async (bp: Blueprint) => {
    setLaunchResult(`Attempting launch of ${bp.name}...`);
    try {
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

      {error && <div className="alert alert-warning mb-4">{error}</div>}
      {launchResult && <div className="alert alert-success mb-4">{launchResult}</div>}

      {/* Search and Filters */}
      <div className="card bg-base-100 shadow-xl mb-6">
        <div className="card-body">
          <div className="flex flex-col md:flex-row gap-4">
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
            <div>
              <label className="label">
                <span className="label-text">Category</span>
              </label>
              <select className="select select-bordered w-full max-w-xs" value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                {categories.map(cat => <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>)}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Featured Blueprints */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
          <Star className="h-6 w-6 text-yellow-500" />
          Featured Blueprints
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {blueprints.filter(bp => bp.featured).map((blueprint) => (
            <div key={blueprint.id} className="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  {blueprint.installed && <span className="badge badge-success badge-sm">Installed</span>}
                  <div className="flex items-center gap-1 text-yellow-500">
                    <Star className="h-4 w-4" />
                    <span className="text-sm font-medium">{blueprint.popularity}</span>
                  </div>
                </div>

                <h3 className="card-title mb-2">{blueprint.name}</h3>
                <p className="text-sm text-gray-500 mb-4">{blueprint.description}</p>

                <div className="divider my-2"></div>

                <div className="space-y-2 text-sm mb-4">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Category:</span>
                    <Badge type="info" size="sm">{blueprint.category}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Version:</span>
                    <span className="font-medium">{blueprint.version}</span>
                  </div>
                </div>

                <div className="card-actions justify-end">
                  <button className="btn btn-outline btn-sm">
                    <Eye className="h-4 w-4 mr-1" />
                    Details
                  </button>
                  {blueprint.installed ? (
                    <button className="btn btn-secondary btn-sm">
                      <Download className="h-4 w-4 mr-1" />
                      Update
                    </button>
                  ) : (
                    <button className="btn btn-primary btn-sm">
                      <Plus className="h-4 w-4 mr-1" />
                      Install
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><LoadingSpinner /></div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredBlueprints.map((blueprint) => (
              <div key={blueprint.id} className="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow">
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
                    <button className="btn btn-outline btn-sm">
                      <Eye className="h-4 w-4 mr-1" />
                      Details
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={() => handleLaunch(blueprint)}>
                      <Play className="h-4 w-4 mr-1" />
                      Launch
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {filteredBlueprints.length === 0 && (
            <div className="card bg-base-100 shadow-xl text-center py-12 mt-8">
              <div className="mb-4">
                <Book className="h-16 w-16 mx-auto text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No blueprints found</h3>
              <p className="text-gray-500 mb-4">
                {searchTerm ? 'No blueprints match your search criteria' : 'Try adjusting your filters'}
              </p>
              <button className="btn btn-outline" onClick={() => {
                setSearchTerm('');
                setCategoryFilter('all');
              }}>
                Reset Filters
              </button>
            </div>
          )}
        </>
      )}

      <div className="mt-6 text-xs opacity-60">
        Data source: /v1/blueprints (or demo). Use swarm-cli for full install/launch.
      </div>
    </div>
  );
}