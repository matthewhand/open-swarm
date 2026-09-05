import { agentRole, fallbackBlueprintSource, normalizeAgentRole } from './agentRoles'
import type { AgentRole } from './api'
import type { TeamRoster } from './teamRosters'

/** Distinctive injected fixture string for tests (never a secret). */
export const REQ42_INJECTED_FIXTURE = 'REQ42_INJECTED_FIXTURE_MARKER'

export type DefinitionKind = 'role' | 'blueprint' | 'team'

export const ROLE_BRIEFS: Record<string, string> = {
  support:
    'Support is Socratic: it talks about the other agents and how this team is wired. It asks one clarifying question at a time, offers a short multiple-choice when you are stuck, and never takes over the work.',
  gate:
    'Gate is a YES/NO classifier for a pending tool call. YES means dangerous (elicit the operator); NO means safe (proceed). If no gate is wired on the roster, the gate is fail-open — every tool call is approved and you are never asked.',
  skeptic:
    'Skeptic is a bounded retry reviewer. It sees the original prompt plus the agent’s output. First line: YES if accomplished, NO if not. On NO it hands concise findings back (max 2 retries). On YES it stops. It does not nag.',
  chief_of_staff:
    'Chief of Staff (CoS) talks to any team. It routes the operator to the right roster and coordinates across teams-of-teams instead of doing the specialist work itself.',
  cos:
    'Chief of Staff (CoS) talks to any team. It routes the operator to the right roster and coordinates across teams-of-teams instead of doing the specialist work itself.',
  suggestions:
    'Suggestions prepares a short list of quick-select prompts. A consumer with Use suggestions on shows those as chips after each turn, including before the first message. Clicking a chip sends that exact string. Chips are chrome, not extra LLM context.',
  engineer:
    'Engineer implements the quoted work. It writes only after a gate or CoS has unblocked it. It is a specialist seat (as_tool / handoff), not an extra Grok chrome row.',
  default:
    'This is a worker blueprint: it runs its own system prompt, tools, and handoffs. It is not a gate, skeptic, Support, Chief of Staff, engineer, or suggestions seat.',
}

export const TEAM_BRIEF =
  'A team is a roster of members that can hand off or be invoked as tools. The operator can talk to the whole team or a single member. Role seats (Support, gate, skeptic, CoS) change how work is approved, reviewed, or routed.'

export const BLUEPRINT_BRIEF =
  'A blueprint is the Python/API recipe for an agent: instructions, tools, metadata, and as-tool / handoff wiring. The runtime injects extra context on top of this source when the agent runs.'

export const MISSING_MODEL_HINT =
  'No default LLM is configured. The brief above is the static explanation — connect a default model in Settings → LLM profiles to summarise the live source and injected context.'

export function definitionRole(id: string, role?: string | null): AgentRole {
  return agentRole({ id, name: id, role })
}

export function staticExplanation(
  kind: DefinitionKind,
  role: string,
): string {
  if (kind === 'team') return TEAM_BRIEF
  if (kind === 'blueprint' && normalizeAgentRole(role) === 'default') {
    return BLUEPRINT_BRIEF
  }
  return ROLE_BRIEFS[normalizeAgentRole(role)] || ROLE_BRIEFS.default
}

export interface DefinitionInjected {
  system_prompt: string
  tools: Record<string, unknown>
  metadata: Record<string, unknown>
  handoff: string
  extra: string
}

export interface DefaultLlmStatus {
  configured: boolean
  model: string | null
}

export interface DefinitionContext {
  kind: DefinitionKind
  id: string
  title: string
  role: string
  explanation: string
  source: string
  injected: DefinitionInjected
  default_llm: DefaultLlmStatus
}

export interface DefinitionSummary {
  kind: DefinitionKind
  id: string
  configured: boolean
  model: string | null
  summary: string | null
  injected_extra?: string
}

export function localDefinitionContext(
  kind: DefinitionKind,
  id: string,
  opts?: { role?: string | null; extra?: string; team?: TeamRoster | null },
): DefinitionContext {
  const role = definitionRole(id, opts?.role)
  const explanation = staticExplanation(kind, role)
  const source =
    kind === 'team'
      ? JSON.stringify(
          opts?.team || { id, name: id, description: '', members: [] },
          null,
          2,
        )
      : fallbackBlueprintSource(id, role)
  const extra = opts?.extra ?? defaultExtra(kind, role)
  return {
    kind,
    id,
    title: kind === 'team' ? opts?.team?.name || id : id,
    role,
    explanation,
    source,
    injected: {
      system_prompt: explanation,
      tools: {},
      metadata: { id, kind, role },
      handoff: handoffNote(kind, role),
      extra,
    },
    default_llm: { configured: false, model: null },
  }
}

export function defaultExtra(kind: DefinitionKind, role: string): string {
  if (role === 'gate') {
    return 'Runtime injects the pending tool name and arguments before classify.'
  }
  if (role === 'skeptic') {
    return 'Runtime injects the original prompt plus the latest agent output.'
  }
  if (role === 'support') {
    return 'Runtime injects the visible agent/team roster so Support can talk about them.'
  }
  if (role === 'chief_of_staff' || role === 'cos') {
    return 'Runtime injects the list of teams CoS may address.'
  }
  if (role === 'suggestions') {
    return 'Runtime injects the latest consumer turn so the specialist can propose the next chips.'
  }
  if (role === 'engineer') {
    return 'Runtime injects the quoted issue and feasibility so the engineer may write.'
  }
  if (kind === 'team') {
    return 'Runtime injects member as-tool / handoff handles for this roster.'
  }
  return 'Runtime may inject MCP tool schemas and memory snippets on top of this source.'
}

export function handoffNote(kind: DefinitionKind, role: string): string {
  if (role === 'gate') {
    return 'Gate is invoked as_tool on a pending tool call (YES/NO). Unwired gate is fail-open.'
  }
  if (role === 'skeptic') {
    return 'Skeptic is invoked as_tool after a run; findings feed a bounded retry (max 2).'
  }
  if (role === 'support') {
    return 'Support talks about other agents; it does not take over their tools.'
  }
  if (role === 'chief_of_staff' || role === 'cos') {
    return 'CoS can address any team roster (talk-to-any-team).'
  }
  if (role === 'suggestions') {
    return 'Suggestions is invoked as_tool after a consumer turn (and on an empty thread for kickstart).'
  }
  if (role === 'engineer') {
    return 'Engineer is invoked as_tool / handoff by CoS after a quoted issue.'
  }
  if (kind === 'team') {
    return 'Team members may be addressed together or invoked as tools.'
  }
  return 'No extra as-tool / handoff seats declared.'
}

/** Prompt sent to the default LLM. Tests assert the fixture extra is present. */
export function buildSummarizePrompt(ctx: DefinitionContext): string {
  return [
    `Kind: ${ctx.kind}`,
    `Id: ${ctx.id}`,
    '',
    '## Human brief',
    ctx.explanation,
    '',
    '## Source',
    ctx.source.slice(0, 12_000),
    '',
    '## Injected system prompt',
    ctx.injected.system_prompt,
    '',
    '## Injected tools',
    JSON.stringify(ctx.injected.tools),
    '',
    '## Injected metadata',
    JSON.stringify(ctx.injected.metadata),
    '',
    '## Injected handoff / as-tool wiring',
    ctx.injected.handoff,
    '',
    '## Extra runtime context',
    ctx.injected.extra,
  ].join('\n')
}

export type DefinitionSummarizer = (prompt: string, ctx: DefinitionContext) => Promise<string>

/** Use the provided stub/default LLM. Does not invent a second inference stack. */
export async function summarizeWithLlm(
  ctx: DefinitionContext,
  llm: DefinitionSummarizer,
): Promise<DefinitionSummary> {
  if (!ctx.default_llm.configured) {
    return {
      kind: ctx.kind,
      id: ctx.id,
      configured: false,
      model: null,
      summary: null,
      injected_extra: ctx.injected.extra,
    }
  }
  const prompt = buildSummarizePrompt(ctx)
  const summary = await llm(prompt, ctx)
  return {
    kind: ctx.kind,
    id: ctx.id,
    configured: true,
    model: ctx.default_llm.model,
    summary,
    injected_extra: ctx.injected.extra,
  }
}
