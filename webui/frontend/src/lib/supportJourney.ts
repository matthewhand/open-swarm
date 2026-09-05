/**
 * REQ-137: first-run Support journey chips (Chat empty state + Agent Router).
 * Labels match backend `swarm.core.support_journey.SUPPORT_KICKSTART_CANNED`.
 */

export const SUPPORT_JOURNEY_FIXTURE = 'ONBOARD_JOURNEY_CLI_API_REMOTE'

export const SUPPORT_JOURNEY_KICKSTART = [
  'Create a team',
  'Add a remote',
  'Wire a CLI',
  'How do CLI, API, and remotes differ?',
] as const

export function isSupportJourneyConsumer(id: string | null | undefined): boolean {
  const ident = (id || '').trim().toLowerCase()
  return ident === 'support' || ident === 'starter-support'
}

export function supportJourneyKickstart(): string[] {
  return [...SUPPORT_JOURNEY_KICKSTART]
}
