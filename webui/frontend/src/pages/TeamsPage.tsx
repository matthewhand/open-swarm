import React, { useState } from 'react';
import { Button, Card, Alert, Badge } from '../components/DaisyUI';
import { Users, Plus, Edit, Trash2, Search } from 'lucide-react';

// Mock data for teams
const mockTeams = [
  {
    id: 1,
    name: 'Code Review Team',
    description: 'Automated code review and quality assurance',
    status: 'active' as const,
    members: 4,
    created: '2024-01-15',
  },
  {
    id: 2,
    name: 'Documentation Squad',
    description: 'Technical writing and documentation generation',
    status: 'idle' as const,
    members: 3,
    created: '2024-02-20',
  },
  {
    id: 3,
    name: 'Data Processing',
    description: 'Large-scale data analysis and transformation',
    status: 'error' as const,
    members: 5,
    created: '2024-03-10',
  },
  {
    id: 4,
    name: 'Research Assistants',
    description: 'Web research and information synthesis',
    status: 'active' as const,
    members: 2,
    created: '2024-03-25',
  },
];

const statusColors = {
  active: 'success',
  idle: 'warning',
  error: 'error',
};

const TeamsPage = () => {
  const [teams, setTeams] = useState(mockTeams);
  const [searchTerm, setSearchTerm] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const filteredTeams = teams.filter(team =>
    team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    team.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDelete = (id: number) => {
    setTeams(teams.filter(team => team.id !== id));
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Users className="h-8 w-8" />
            Team Management
          </h1>
          <p className="text-gray-500 mt-1">Create and manage your AI teams</p>
        </div>
        <div className="flex gap-2 mt-4 lg:mt-0">
          <Button variant="primary" onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </Button>
          <Button variant="outline">
            <Search className="h-4 w-4 mr-2" />
            Advanced Search
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <Card bordered className="mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <label className="label">
              <span className="label-text">Search Teams</span>
            </label>
            <input
              type="text"
              placeholder="Search by name or description..."
              className="input input-bordered w-full"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div>
            <label className="label">
              <span className="label-text">Status Filter</span>
            </label>
            <select className="select select-bordered w-full max-w-xs">
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredTeams.map((team) => (
          <Card key={team.id} bordered className="hover:shadow-lg transition-shadow">
            <div className="card-body">
              <div className="flex justify-between items-start mb-2">
                <Badge type={statusColors[team.status]}>
                  {team.status.charAt(0).toUpperCase() + team.status.slice(1)}
                </Badge>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" className="btn-xs">
                    <Edit className="h-3 w-3" />
                  </Button>
                  <Button variant="ghost" size="sm" className="btn-xs" onClick={() => handleDelete(team.id)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              <h2 className="card-title mb-1">{team.name}</h2>
              <p className="text-sm text-gray-500 mb-3">{team.description}</p>

              <div className="divider my-2"></div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Members:</span>
                  <span className="font-medium">{team.members}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Created:</span>
                  <span className="font-medium">{team.created}</span>
                </div>
              </div>

              <div className="card-actions justify-end mt-4">
                <Button variant="outline" size="sm">
                  View Details
                </Button>
                <Button variant="primary" size="sm">
                  Launch
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {filteredTeams.length === 0 && (
        <Card bordered className="text-center py-12">
          <div className="mb-4">
            <Users className="h-16 w-16 mx-auto text-gray-400" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No teams found</h3>
          <p className="text-gray-500 mb-4">
            {searchTerm ? 'No teams match your search criteria' : 'Create your first team to get started'}
          </p>
          <Button variant="primary" onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Team
          </Button>
        </Card>
      )}

      {/* Create Team Modal */}
      {showCreateModal && (
        <div className="modal modal-open">
          <div className="modal-box">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Create New Team
            </h3>
            <p className="py-4 text-gray-500">
              Set up a new AI team with custom configuration
            </p>

            <div className="space-y-4">
              <div>
                <label className="label">
                  <span className="label-text">Team Name</span>
                </label>
                <input type="text" placeholder="e.g., Code Review Team" className="input input-bordered w-full" />
              </div>

              <div>
                <label className="label">
                  <span className="label-text">Description</span>
                </label>
                <textarea placeholder="Describe the team's purpose..." className="textarea textarea-bordered w-full h-24"></textarea>
              </div>

              <div>
                <label className="label">
                  <span className="label-text">Team Size</span>
                </label>
                <input type="number" placeholder="Number of agents" className="input input-bordered w-full" min="1" max="10" />
              </div>
            </div>

            <div className="modal-action flex gap-2">
              <Button variant="outline" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button variant="primary">
                Create Team
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamsPage;
