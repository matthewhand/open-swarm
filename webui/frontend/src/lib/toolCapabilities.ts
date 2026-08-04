// Mirror of swarm.core.tool_capabilities resolution for live preview in the
// Builder: map required capabilities to selected MCP providers, preferring
// non-auth ones; an unmet optional need never blocks.

export interface McpServerInfo {
  name: string
  provides: string[]
  command: string
  args: string[]
  needs_auth: boolean
  auth_env: string[]
  note: string
}

export type Level = 'mandatory' | 'optional'

export interface CapResolution {
  satisfied: Record<string, string> // capability -> server name
  missingMandatory: string[]
  skippedOptional: string[]
}

/** Resolve required capabilities against the chosen servers, non-auth first.
 *  `authAvailable` marks which auth servers have their key present (so an
 *  auth-only capability can still resolve); default treats auth as usable so the
 *  preview matches a configured key. */
export function resolveCapabilities(
  requirements: Record<string, Level>,
  servers: McpServerInfo[],
  authAvailable: (s: McpServerInfo) => boolean = () => true,
): CapResolution {
  const res: CapResolution = { satisfied: {}, missingMandatory: [], skippedOptional: [] }
  for (const [cap, level] of Object.entries(requirements)) {
    const candidates = servers
      .filter((s) => s.provides.includes(cap))
      .sort((a, b) => Number(a.needs_auth) - Number(b.needs_auth) || a.name.localeCompare(b.name))
    const usable = candidates.find((s) => !s.needs_auth || authAvailable(s))
    if (usable) res.satisfied[cap] = usable.name
    else (level === 'mandatory' ? res.missingMandatory : res.skippedOptional).push(cap)
  }
  return res
}

/** The non-auth server to suggest for a capability (or any provider if none). */
export function suggestServer(cap: string, catalog: McpServerInfo[]): McpServerInfo | undefined {
  const providers = catalog.filter((s) => s.provides.includes(cap))
  return providers.find((s) => !s.needs_auth) ?? providers[0]
}

/** Build the emitted config: mcpServers (chosen) + tool_requirements. */
export function buildToolsConfig(
  requirements: Record<string, Level>,
  servers: McpServerInfo[],
): Record<string, unknown> {
  const mcpServers: Record<string, unknown> = {}
  for (const s of servers) {
    const entry: Record<string, unknown> = { command: s.command, args: s.args, provides: s.provides }
    if (s.needs_auth) entry.env = Object.fromEntries(s.auth_env.map((k) => [k, `\${${k}}`]))
    mcpServers[s.name] = entry
  }
  return { mcpServers, tool_requirements: requirements }
}
