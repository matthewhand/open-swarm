import { OVERSIGHT_ROLES, rolesHeldBy, type OversightRole } from '../../lib/agent-roles'
import type { Agent } from '../../types/agent'
import type { RoleAssignments } from '../../lib/agent-roles'

interface AgentRolesProps {
  subject: Agent
  agents: Agent[]
  assignments: RoleAssignments
  onAssign: (role: OversightRole, assigneeId: string | null) => void
}

export function AgentRoles({ subject, agents, assignments, onAssign }: AgentRolesProps) {
  const map = assignments[subject.agent_id] || {}
  const held = rolesHeldBy(assignments, subject.agent_id)

  return (
    <div className="space-y-1.5">
      <div className="font-semibold text-base-content/50 uppercase tracking-wider text-[10px]">
        Oversight roles
      </div>
      <p className="text-base-content/60 leading-relaxed">
        Assign other agents to auto-review this one. The assignee becomes that role.
      </p>
      {held.length > 0 && (
        <p className="text-[11px] text-primary">
          This agent is {held.map((id) => OVERSIGHT_ROLES.find((r) => r.id === id)?.label).join(', ')}{' '}
          for others.
        </p>
      )}
      <div className="space-y-2">
        {OVERSIGHT_ROLES.map((role) => (
          <label key={role.id} className="block">
            <span className="text-[11px] font-medium text-base-content/70">{role.label}</span>
            <select
              className="select select-bordered select-xs w-full mt-0.5"
              aria-label={role.label}
              value={map[role.id] || ''}
              onChange={(e) => onAssign(role.id, e.target.value || null)}
            >
              <option value="">None</option>
              {agents.map((agent) => (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {agent.customName || agent.name}
                </option>
              ))}
            </select>
            <span className="block text-[10px] text-base-content/45 mt-0.5">{role.hint}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
