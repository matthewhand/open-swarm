// Skill attach + inline chip helpers (REQ-212).
// Discovery: GET /v1/skills/ walks <project>/skills/**/SKILL.md.

export interface SkillInfo {
  name: string
  description: string
  assets: string[]
  id?: string
  path?: string
  instructions?: string
  found?: boolean
  error?: string
}

export type SkillRefKind = 'slash' | 'path' | 'bare'

export interface SkillRef {
  name: string
  raw: string
  kind: SkillRefKind
  start: number
  end: number
}

export type SkillSegment =
  | { type: 'text'; text: string }
  | { type: 'skill'; ref: SkillRef }

const SKILL_NAME = '[a-z0-9-]{1,64}'
const SKILL_REF_RE = new RegExp(
  `(?:\\/skill\\s+(${SKILL_NAME})|skills\\/(${SKILL_NAME})\\/SKILL\\.md|skill:(${SKILL_NAME}))`,
  'gi',
)

/** The request snippet that applies a skill to a cli_agent call. */
export function buildSkillRequest(skill: string | null): Record<string, unknown> | null {
  if (!skill) return null
  return { model: 'cli_agent', params: { skill } }
}

export function normalizeSkillName(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .toLowerCase()
}

export function uniqueSkillNames(names: Iterable<string>): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of names) {
    const name = normalizeSkillName(raw)
    if (!name || seen.has(name)) continue
    seen.add(name)
    out.push(name)
  }
  return out
}

/** Parse `/skill name` tokens from composer or chat text. */
export function parseComposerSkillNames(text: string): string[] {
  const names: string[] = []
  const re = new RegExp(`\\/skill\\s+(${SKILL_NAME})`, 'gi')
  let match: RegExpExecArray | null
  while ((match = re.exec(String(text || ''))) !== null) {
    names.push(match[1])
  }
  return uniqueSkillNames(names)
}

/** Params to attach one or more skills on a chat/completions turn. */
export function buildSkillParams(names: Iterable<string>): Record<string, unknown> {
  const skills = uniqueSkillNames(names)
  if (skills.length === 0) return {}
  if (skills.length === 1) return { skill: skills[0], skills }
  return { skills }
}

function fenceRanges(text: string): Array<[number, number]> {
  const ranges: Array<[number, number]> = []
  const re = /```[\s\S]*?```/g
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    ranges.push([match.index, match.index + match[0].length])
  }
  return ranges
}

function inRange(index: number, ranges: Array<[number, number]>): boolean {
  return ranges.some(([start, end]) => index >= start && index < end)
}

function refKind(raw: string): SkillRefKind {
  if (raw.startsWith('/skill')) return 'slash'
  if (raw.includes('SKILL.md')) return 'path'
  return 'bare'
}

/** Find inline skill refs outside fenced code. */
export function findSkillRefs(text: string): SkillRef[] {
  const source = String(text || '')
  if (!source) return []
  const fences = fenceRanges(source)
  const refs: SkillRef[] = []
  SKILL_REF_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = SKILL_REF_RE.exec(source)) !== null) {
    if (inRange(match.index, fences)) continue
    const name = normalizeSkillName(match[1] || match[2] || match[3])
    if (!name) continue
    refs.push({
      name,
      raw: match[0],
      kind: refKind(match[0]),
      start: match.index,
      end: match.index + match[0].length,
    })
  }
  return refs
}

export function splitSkillRefs(text: string): SkillSegment[] {
  const source = String(text || '')
  const refs = findSkillRefs(source)
  if (refs.length === 0) return source ? [{ type: 'text', text: source }] : []
  const segments: SkillSegment[] = []
  let cursor = 0
  for (const ref of refs) {
    if (ref.start > cursor) {
      segments.push({ type: 'text', text: source.slice(cursor, ref.start) })
    }
    segments.push({ type: 'skill', ref })
    cursor = ref.end
  }
  if (cursor < source.length) {
    segments.push({ type: 'text', text: source.slice(cursor) })
  }
  return segments
}

export function skillSourcePath(skill: Pick<SkillInfo, 'name' | 'path'>): string {
  return skill.path || `skills/${skill.name}/SKILL.md`
}

export function skillLookupError(name: string): string {
  return `Skill '${name}' not found. Add a SKILL.md under skills/ (see docs/SKILLS.md).`
}
