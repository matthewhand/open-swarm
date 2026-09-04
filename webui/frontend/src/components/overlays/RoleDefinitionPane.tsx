/**
 * Role-definition pane (REQ-48 host for #356).
 *
 * Leads with a brief human explanation. Full LLM summarise / Edit code is
 * owned by the role-badge issue — this sheet only keeps Chat mounted.
 */

export const DEFAULT_ROLE_ID = 'support'

const ROLE_BRIEFS: Record<string, { title: string; explanation: string }> = {
  support: {
    title: 'Support',
    explanation:
      'Socratic helper: stays in conversation, asks clarifying questions, and routes work to other seats when a specialist is a better fit.',
  },
  gate: {
    title: 'Gate',
    explanation:
      'YES/NO gate: decides whether a handoff or action proceeds. A NO stops the hop; a YES lets the next agent run.',
  },
  skeptic: {
    title: 'Skeptic',
    explanation:
      'Retry critic: challenges a draft, asks for evidence, and can send the author back for another pass instead of accepting the first answer.',
  },
  cos: {
    title: 'Chief of Staff',
    explanation:
      'Talk-to-any-team seat: holds isolation boundaries and can address other teams without merging their threads.',
  },
}

export function roleBrief(roleId: string): { title: string; explanation: string } {
  const key = roleId.trim().toLowerCase()
  return (
    ROLE_BRIEFS[key] ?? {
      title: roleId.trim() || 'Role',
      explanation:
        'This seat has a role definition. The badge opens this pane so Chat stays mounted while you inspect how it works.',
    }
  )
}

export default function RoleDefinitionPane({ roleId = DEFAULT_ROLE_ID }: { roleId?: string }) {
  const brief = roleBrief(roleId)
  return (
    <div className="space-y-3">
      <h4 className="text-lg font-semibold">{brief.title}</h4>
      <p className="text-sm text-base-content/80" data-testid="role-explanation">
        {brief.explanation}
      </p>
      <p className="text-xs text-base-content/55">
        Edit code and LLM re-summarise land with the role-badge pane. This overlay
        does not replace Chat.
      </p>
    </div>
  )
}
