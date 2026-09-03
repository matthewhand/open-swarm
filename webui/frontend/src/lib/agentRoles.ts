import type { AgentRole, Blueprint } from './api'
import { SUPPORT_AGENT_ID, SYNTHETIC_SUPPORT, isSupportAgent } from './supportAgent'

/** Example roles that demonstrate blueprint design (REQ-25). */
export const EXAMPLE_ROLES = ['support', 'gate', 'skeptic'] as const
export type ExampleRole = (typeof EXAMPLE_ROLES)[number]

export const GATE_AGENT_ID = 'gate'
export const SKEPTIC_AGENT_ID = 'skeptic'

const ROLE_ALIASES: Record<string, AgentRole> = {
  default: 'default',
  worker: 'default',
  agent: 'default',
  coordinator: 'default',
  support: 'support',
  helper: 'support',
  gate: 'gate',
  tool_gate: 'gate',
  'tool-gate': 'gate',
  toolgate: 'gate',
  skeptic: 'skeptic',
  reviewer: 'skeptic',
  chief_of_staff: 'chief_of_staff',
  'chief-of-staff': 'chief_of_staff',
  chiefofstaff: 'chief_of_staff',
  cos: 'chief_of_staff',
  chief: 'chief_of_staff',
}

export const SYNTHETIC_GATE: Blueprint = {
  id: GATE_AGENT_ID,
  object: 'blueprint',
  name: 'Gate',
  description: 'YES/NO classifier for pending tool calls.',
  abbreviation: null,
  required_mcp_servers: [],
  tags: [],
  installed: true,
  compiled: true,
  role: 'gate',
}

export const SYNTHETIC_SKEPTIC: Blueprint = {
  id: SKEPTIC_AGENT_ID,
  object: 'blueprint',
  name: 'Skeptic',
  description: 'Bounded retry reviewer after a run.',
  abbreviation: null,
  required_mcp_servers: [],
  tags: [],
  installed: true,
  compiled: true,
  role: 'skeptic',
}

const SYNTHETICS: Record<ExampleRole, Blueprint> = {
  support: { ...SYNTHETIC_SUPPORT, role: 'support' },
  gate: SYNTHETIC_GATE,
  skeptic: SYNTHETIC_SKEPTIC,
}

/** Live runtime modules to link when present (do not rewrite them here). */
export const ROLE_RUNTIME_MODULES: Record<ExampleRole, { label: string; path: string }[]> = {
  support: [{ label: 'blueprint_support.py', path: 'src/swarm/blueprints/support/blueprint_support.py' }],
  gate: [{ label: 'tool_gate', path: 'src/swarm/core/tool_gate.py' }],
  skeptic: [{ label: 'skeptic', path: 'src/swarm/core/skeptic.py' }],
}

export const ROLE_FALLBACK_SOURCE: Record<ExampleRole, string> = {
  support: `# Blueprint recipe — Support (Socratic)
# Role = badge + wiring on a Team member. This file is the Python/API recipe.
# Runtime modules (when present): src/swarm/blueprints/support/blueprint_support.py

SUPPORT_INSTRUCTIONS = (
    "You are Support. Talk about the other agents and how this team is wired. "
    "Stay Socratic: ask one clarifying question at a time, offer a short "
    "multiple-choice when the user is stuck, and never take over the work."
)

def ask_user(question: str, choices: list[str] | None = None) -> str:
    """Elicit the operator. MCQ when choices are given; otherwise free text."""
    if choices:
        return f"MCQ: {question} | " + " / ".join(choices)
    return f"ASK: {question}"
`,
  gate: `# Blueprint recipe — Gate (YES/NO)
# Role = badge + wiring on a Team member. This file is the Python/API recipe.
# Runtime module (when present): src/swarm/core/tool_gate.py
# Unwired gate is fail-open: every tool call is approved and the user is never asked.

GATE_INSTRUCTIONS = (
    "You are a tool-call gate. Classify the pending tool call as dangerous or not. "
    "Reply with a single token only: YES if the call is dangerous, NO if it is not. "
    "No punctuation, no explanation."
)

def classify_pending_tool_call(tool_name: str, arguments: dict) -> str:
    """Return YES (dangerous → elicit) or NO (safe → proceed)."""
    raise NotImplementedError("live classifier is swarm.core.tool_gate")
`,
  skeptic: `# Blueprint recipe — Skeptic (bounded retry)
# Role = badge + wiring on a Team member. This file is the Python/API recipe.
# Runtime module (when present): src/swarm/core/skeptic.py
# On YES (accomplished) stop. On NO, hand findings back (max 2 retries). Do not nag.

SKEPTIC_MAX_RETRIES = 2
SKEPTIC_INSTRUCTIONS = (
    "You are a skeptic. You see the original prompt plus the agent's output. "
    "First line: YES if accomplished, NO if not. "
    "If NO, follow with concise findings the original agent can use to retry. "
    "If YES, stop. Do not nag."
)

def run_with_skeptic(prompt: str, output: str) -> str:
    """Review output; retry the original agent at most SKEPTIC_MAX_RETRIES times."""
    raise NotImplementedError("live retry loop is swarm.core.skeptic")
`,
}

export function normalizeAgentRole(value: unknown): AgentRole {
  if (value == null) return 'default'
  const key = String(value).trim().toLowerCase().replace(/\s+/g, '_')
  if (!key) return 'default'
  return ROLE_ALIASES[key] ?? 'default'
}

export function agentRole(agent: {
  id?: string | null
  name?: string | null
  role?: string | null
}): AgentRole {
  const explicit = normalizeAgentRole(agent.role)
  if (explicit !== 'default') return explicit
  if (isSupportAgent({ id: agent.id || '', name: agent.name })) return 'support'
  const id = (agent.id || '').trim().toLowerCase()
  const name = (agent.name || '').trim().toLowerCase()
  if (id === GATE_AGENT_ID || name === 'gate' || name === 'tool gate') return 'gate'
  if (id === SKEPTIC_AGENT_ID || name === 'skeptic') return 'skeptic'
  if (id === 'cos' || id === 'chief' || id === 'chief_of_staff' || name === 'chief of staff') {
    return 'chief_of_staff'
  }
  return normalizeAgentRole(id) === 'default' ? 'default' : normalizeAgentRole(id)
}

export const ROLE_CHIEF_OF_STAFF = 'chief_of_staff'

export const ROLE_BADGE_LABELS: Record<AgentRole, string> = {
  default: '',
  support: 'Support',
  gate: 'Gate',
  skeptic: 'Skeptic',
  chief_of_staff: 'CoS',
}

export function isChiefOfStaff(role: unknown): boolean {
  return normalizeAgentRole(role) === ROLE_CHIEF_OF_STAFF
}

export function roleBadgeLabel(role: unknown): string {
  return ROLE_BADGE_LABELS[normalizeAgentRole(role)]
}

export function roleFromAgent(agent: { role?: unknown; id?: string; name?: string | null }): AgentRole {
  return agentRole(agent)
}

export function isExampleRole(role: string): role is ExampleRole {
  return (EXAMPLE_ROLES as readonly string[]).includes(role)
}

/** Hover-edit is for example roles (or a default row that already has a role blueprint). */
export function showsBlueprintEdit(agent: {
  id?: string | null
  name?: string | null
  role?: string | null
}): boolean {
  return isExampleRole(agentRole(agent))
}

export function roleCssClass(role: AgentRole | string): string {
  return `os-agent-role-${normalizeAgentRole(role)}`
}

export function isExampleRoleAgent(agent: {
  id?: string | null
  name?: string | null
  role?: string | null
}): boolean {
  return showsBlueprintEdit(agent)
}

function hasRole(agents: Blueprint[], role: ExampleRole): boolean {
  return agents.some((agent) => agentRole(agent) === role)
}

/** Inject Support / Gate / Skeptic seats so the three example roles are visible. */
export function ensureExampleRoleAgents(agents: Blueprint[]): Blueprint[] {
  const next = [...agents]
  if (!next.some(isSupportAgent) && !hasRole(next, 'support')) {
    next.unshift(SYNTHETICS.support)
  }
  if (!hasRole(next, 'gate')) next.push(SYNTHETICS.gate)
  if (!hasRole(next, 'skeptic')) next.push(SYNTHETICS.skeptic)
  return next
}

export function sortExampleRolesFirst(agents: Blueprint[]): Blueprint[] {
  const rank = (agent: Blueprint): number => {
    const role = agentRole(agent)
    if (role === 'support') return 0
    if (role === 'gate') return 1
    if (role === 'skeptic') return 2
    return 3
  }
  return [...agents].sort((a, b) => {
    const ra = rank(a)
    const rb = rank(b)
    if (ra !== rb) return ra - rb
    return (a.name || a.id).localeCompare(b.name || b.id)
  })
}

export function exampleRoleAgents(agents: Blueprint[]): Blueprint[] {
  return sortExampleRolesFirst(ensureExampleRoleAgents(agents))
}

export function fallbackBlueprintSource(blueprintId: string, role: AgentRole): string {
  if (isExampleRole(role)) return ROLE_FALLBACK_SOURCE[role]
  return (
    `# Blueprint ${blueprintId}\n` +
    `# No source is published for this agent yet.\n` +
    `# The editor edits a Blueprint (Python/API recipe), not a Team roster.\n`
  )
}

export function runtimeModulesFor(role: AgentRole): { label: string; path: string }[] {
  return isExampleRole(role) ? ROLE_RUNTIME_MODULES[role] : []
}

export { SUPPORT_AGENT_ID }
