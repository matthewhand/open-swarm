export const OVERSIGHT_ROLES = [
  {
    id: 'socratic_skeptic',
    label: 'Socratic skeptic',
    short: 'Skeptic',
    hint: 'Auto-replies after a finished generation',
  },
  {
    id: 'stupidity_checker',
    label: 'Stupidity checker',
    short: 'Checker',
    hint: 'Flags tool calls that may need your approval',
  },
  {
    id: 'taskmaster',
    label: 'Taskmaster',
    short: 'Taskmaster',
    hint: 'Reviews generation output against the request',
  },
] as const

export type OversightRole = (typeof OVERSIGHT_ROLES)[number]['id']

export type RoleMap = Partial<Record<OversightRole, string>>
export type RoleAssignments = Record<string, RoleMap>

export function roleMeta(id: OversightRole) {
  return OVERSIGHT_ROLES.find((r) => r.id === id)!
}

export function setRoleAssignment(
  assignments: RoleAssignments,
  subjectId: string,
  role: OversightRole,
  assigneeId: string | null,
): RoleAssignments {
  const current = { ...(assignments[subjectId] || {}) }
  if (!assigneeId) delete current[role]
  else current[role] = assigneeId
  const next = { ...assignments }
  if (Object.keys(current).length === 0) delete next[subjectId]
  else next[subjectId] = current
  return next
}

export function rolesHeldBy(assignments: RoleAssignments, agentId: string): OversightRole[] {
  const held = new Set<OversightRole>()
  for (const map of Object.values(assignments)) {
    for (const role of OVERSIGHT_ROLES) {
      if (map[role.id] === agentId) held.add(role.id)
    }
  }
  return OVERSIGHT_ROLES.map((r) => r.id).filter((id) => held.has(id))
}

export function buildSkepticPrompt(userText: string, generation: string): string {
  return (
    'You are the Socratic skeptic. A teammate just finished a generation. ' +
    'Reply with 1-3 probing questions that test assumptions, missing edge cases, or hidden costs. ' +
    'Do not redo the task or implement a solution.\n\n' +
    `User request:\n${userText}\n\nGeneration:\n${generation}`
  )
}

export function buildTaskmasterPrompt(userText: string, generation: string): string {
  return (
    'You are the Taskmaster. Review this generation against the user request. ' +
    'Give a short pass/fail, gaps, and the next concrete fix if needed. Do not redo the whole task.\n\n' +
    `User request:\n${userText}\n\nGeneration:\n${generation}`
  )
}

export function buildStupidityPrompt(userText: string, generation: string): string {
  return (
    'You are the Stupidity checker. Inspect this assistant output for tool calls, shell commands, ' +
    'deletes, sends, payments, or other actions that should wait for a human. ' +
    'First line must be YES or NO. Then one short reason.\n\n' +
    `User request:\n${userText}\n\nGeneration:\n${generation}`
  )
}

export function parseApprovalVerdict(text: string): { needsApproval: boolean; reason: string } {
  const trimmed = (text || '').trim()
  const first = trimmed.split(/\n/, 1)[0] || ''
  const needsApproval = /^\s*yes\b/i.test(first)
  const reason = trimmed.replace(/^\s*(yes|no)\b[:.\-\s]*/i, '').trim() || trimmed
  return { needsApproval, reason }
}

const TOOLISH =
  /\b(tool call|function call|run terminal|shell|rm -|sudo |curl |wget |drop table|delete from|send email|wire transfer|chmod |kubectl |terraform apply)\b/i

export function looksLikeToolUse(text: string): boolean {
  return TOOLISH.test(text || '')
}
