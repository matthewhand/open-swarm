import React, { useState } from 'react';
import { Button, Card, Alert, Badge } from '../components/DaisyUI';
import { Book, Plus, Search, Star, Download, Eye } from 'lucide-react';

// Mock data for blueprints
const mockBlueprints = [
  {
    id: 1,
    name: 'Codey',
    description: 'Advanced code generation and review assistant',
    category: 'Development',
    version: '1.2.3',
    popularity: 4.8,
    installed: true,
    featured: true,
  },
  {
    id: 2,
    name: 'Researcher',
    description: 'Web research and information synthesis',
    category: 'Research',
    version: '2.1.0',
    popularity: 4.5,
    installed: false,
    featured: false,
  },
  {
    id: 3,
    name: 'Data Analyst',
    description: 'Statistical analysis and data visualization',
    category: 'Analytics',
    version: '1.0.5',
    popularity: 4.2,
    installed: true,
    featured: false,
  },
  {
    id: 4,
    name: 'Documentation Writer',
    description: 'Technical writing and API documentation',
    category: 'Writing',
    version: '1.1.2',
    popularity: 4.7,
    installed: false,
    featured: true,
  },
  {
    id: 5,
    name: 'Customer Support',
    description: 'Automated customer service and ticketing',
    category: 'Support',
    version: '3.0.1',
    popularity: 4.3,
    installed: true,
    featured: false,
  },
  {
    id: 6,
    name: 'Content Creator',
    description: 'Blog posts, social media, and marketing content',
    category: 'Marketing',
    version: '2.2.0',
    popularity: 4.6,
    installed: false,
    featured: true,
  },
];

const BlueprintsPage = () => {
  const [blueprints, setBlueprints] = useState(mockBlueprints);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [showInstallModal, setShowInstallModal] = useState(false);
  const [selectedBlueprint, setSelectedBlueprint] = useState<any>(null);

  const categories = ['all', ...new Set(blueprints.map(bp => bp.category))];

  const filteredBlueprints = blueprints.filter(blueprint => {
    const matchesSearch = blueprint.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         blueprint.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || blueprint.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleInstall = (blueprint: any) => {
    setSelectedBlueprint(blueprint);
    setShowInstallModal(true);
  };

  const confirmInstall = () => {
    if (selectedBlueprint) {
      setBlueprints(blueprints.map(bp =>
        bp.id === selectedBlueprint.id ? { ...bp, installed: true } : bp
      ));
      setShowInstallModal(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">
          <Book className="h-8 w-8" />
          Blueprint Library
        </h1>
        <p className="text-gray-500">Browse and install AI blueprints for your projects</p>
      </div>

      {/* Featured Blueprints */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
          <Star className="h-6 w-6 text-yellow-500" />
          Featured Blueprints
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {blueprints.filter(bp => bp.featured).map((blueprint) => (
            <Card key={blueprint.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  {blueprint.installed && <Badge type="success" size="sm">Installed</Badge>}
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
                  <Button variant="outline" size="sm">
                    <Eye className="h-4 w-4 mr-1" />
                    Details
                  </Button>
                  {blueprint.installed ? (
                    <Button variant="secondary" size="sm">
                      <Download className="h-4 w-4 mr-1" />
                      Update
                    </Button>
                  ) : (
                    <Button variant="primary" size="sm" onClick={() => handleInstall(blueprint)}>
                      <Plus className="h-4 w-4 mr-1" />
                      Install
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Search and Filters */}
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
              <button className="btn join-item">
                <Search className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div>
            <label className="label">
              <span className="label-text">Category</span>
            </label>
            <select
              className="select select-bordered w-full max-w-xs"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              {categories.map(category => (
                <option key={category} value={category}>
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* All Blueprints */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">All Blueprints</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBlueprints.map((blueprint) => (
            <Card key={blueprint.id} bordered className="hover:shadow-lg transition-shadow">
              <div className="card-body">
                <div className="flex justify-between items-start mb-2">
                  {blueprint.installed && <Badge type="success" size="sm">Installed</Badge>}
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
                  <Button variant="outline" size="sm">
                    <Eye className="h-4 w-4 mr-1" />
                    Details
                  </Button>
                  {blueprint.installed ? (
                    <Button variant="secondary" size="sm">
                      <Download className="h-4 w-4 mr-1" />
                      Update
                    </Button>
                  ) : (
                    <Button variant="primary" size="sm" onClick={() => handleInstall(blueprint)}>
                      <Plus className="h-4 w-4 mr-1" />
                      Install
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {filteredBlueprints.length === 0 && (
        <Card bordered className="text-center py-12 mt-8">
          <div className="mb-4">
            <Book className="h-16 w-16 mx-auto text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No blueprints found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'No blueprints match your search criteria' : 'Try adjusting your filters'}
          </p>
          <Button variant="outline" onClick={() => {
            setSearchTerm('');
            setCategoryFilter('all');
          }}>
            Reset Filters
          </Button>
        </Card>
      )}

      {/* Install Confirmation Modal */}
      {showInstallModal && selectedBlueprint && (
        <div className="modal modal-open">
          <div className="modal-box">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Install Blueprint
            </h3>
            <p className="py-4 text-gray-500">
              Confirm installation of {selectedBlueprint.name}
            </p>

            <div className="mb-6">
              <Alert type="info" className="mb-4">
                This will install the blueprint and all required dependencies.
              </Alert>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="font-medium">Name:</span>
                  <span>{selectedBlueprint.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Version:</span>
                  <span>{selectedBlueprint.version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Category:</span>
                  <span>{selectedBlueprint.category}</span>
                </div>
              </div>
            </div>

            <div className="modal-action flex gap-2">
              <Button variant="outline" onClick={() => setShowInstallModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={confirmInstall}>
                <Plus className="h-4 w-4 mr-1" />
                Install Blueprint
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BlueprintsPage;
