/**
 * Static parse of openai-agents persona definitions (REQ-81 / #433).
 *
 * Mirrors `swarm.core.persona_parse`. Never executes source. Variable names
 * are skipped — unknown / unparsable source is count 1 and no invented names.
 */

export interface BlueprintPersona {
  name: string
}

export interface PersonaParseResult {
  count: number
  personas: BlueprintPersona[]
  parsed: boolean
}

export const UNPARSED_PERSONAS: PersonaParseResult = {
  count: 1,
  personas: [],
  parsed: false,
}

const PERSONA_CTORS = new Set(['Agent', 'make_agent', '_make_agent'])

const CALL_RE =
  /\b(Agent|make_agent|_make_agent)\s*\(([\s\S]*?)\)/g
const NAME_KW_RE = /(?:^|[,(\s])name\s*=\s*(['"])((?:\\.|(?!\1).)*)\1/
const FIRST_STR_RE = /^\s*(['"])((?:\\.|(?!\1).)*)\1/

export function parseOpenaiAgentPersonas(source: string | null | undefined): PersonaParseResult {
  if (typeof source !== 'string' || !source.trim()) return { ...UNPARSED_PERSONAS }
  const names: string[] = []
  const seen = new Set<string>()
  CALL_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = CALL_RE.exec(source)) !== null) {
    const ctor = match[1]
    if (!ctor || !PERSONA_CTORS.has(ctor)) continue
    const args = match[2] || ''
    const name = literalName(args)
    if (!name || seen.has(name)) continue
    seen.add(name)
    names.push(name)
  }
  if (!names.length) return { ...UNPARSED_PERSONAS }
  return {
    count: names.length,
    personas: names.map((name) => ({ name })),
    parsed: true,
  }
}

function literalName(args: string): string | null {
  const kw = args.match(NAME_KW_RE)
  if (kw?.[2]?.trim()) return kw[2].trim()
  const first = args.match(FIRST_STR_RE)
  if (first?.[2]?.trim()) return first[2].trim()
  return null
}

export function normalizePersonaResult(raw: unknown): PersonaParseResult {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { ...UNPARSED_PERSONAS }
  const rec = raw as Record<string, unknown>
  const personas: BlueprintPersona[] = []
  const list = Array.isArray(rec.personas) ? rec.personas : []
  for (const item of list) {
    if (!item || typeof item !== 'object') continue
    const name = typeof (item as { name?: unknown }).name === 'string'
      ? (item as { name: string }).name.trim()
      : ''
    if (name) personas.push({ name })
  }
  if (!personas.length) return { ...UNPARSED_PERSONAS }
  const count = typeof rec.count === 'number' && rec.count > 0 ? rec.count : personas.length
  return { count, personas, parsed: true }
}

export function personaInitials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return '?'
  const parts = trimmed.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0]![0] || ''}${parts[1]![0] || ''}`.toUpperCase()
  }
  return trimmed.slice(0, 2).toUpperCase()
}
