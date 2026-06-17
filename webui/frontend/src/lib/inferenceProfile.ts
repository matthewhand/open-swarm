// Mirror of swarm.core.inference_profile (distance-from-ideal) for live preview
// in the Builder. The blueprint declares a target on the axes it cares about;
// we pick the candidate (cli or cli@model) closest in Euclidean distance over
// only those axes — unspecified axes never penalize.

export const TRAITS = ['intelligence', 'speed', 'cost'] as const
export type Trait = (typeof TRAITS)[number]
export type TraitVector = Record<string, number>

const DEFAULT = 0.5

const clamp = (v: number): number => (Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : DEFAULT)

/** Axes the caller actually specified (known axes only), clamped to [0,1]. */
function targetAxes(desired: TraitVector): Partial<Record<Trait, number>> {
  const out: Partial<Record<Trait, number>> = {}
  for (const t of TRAITS) if (t in desired) out[t] = clamp(desired[t])
  return out
}

/** Negated Euclidean distance over requested axes — higher is a better match. */
export function score(desired: TraitVector, capability: TraitVector): number {
  const target = targetAxes(desired)
  let sum = 0
  for (const t of Object.keys(target) as Trait[]) {
    const c = clamp(capability[t] ?? DEFAULT)
    sum += (target[t]! - c) ** 2
  }
  return -Math.sqrt(sum)
}

/** Candidate backends ranked best-first; ties (incl. no axes) break by name. */
export function rank(
  desired: TraitVector,
  candidates: Record<string, TraitVector>,
): { name: string; score: number }[] {
  return Object.entries(candidates)
    .map(([name, cap]) => ({ name, score: score(desired, cap) }))
    .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name))
}

/** The single closest-matching candidate name, or null. Null when there are no
 *  candidates, or when `desired` names no known axis (nothing to score on, so we
 *  decline rather than return an arbitrary alphabetically-first backend). */
export function resolve(desired: TraitVector, candidates: Record<string, TraitVector>): string | null {
  if (Object.keys(targetAxes(desired)).length === 0) return null
  const r = rank(desired, candidates)
  return r.length ? r[0].name : null
}

/** Split a candidate key into [cli, model | null] ("cli@model"). */
export function splitCandidate(key: string): [string, string | null] {
  const i = key.indexOf('@')
  return i === -1 ? [key, null] : [key.slice(0, i), key.slice(i + 1)]
}

export interface ModelRow {
  cli: string
  model: string
  traits: TraitVector
}

/** Emit a cli_agents config carrying edited per-provider `traits` and per-model
 *  `models[<id>].traits`, ready to paste into a swarm config. */
export function buildTraitsConfig(
  cliTraits: Record<string, TraitVector>,
  modelRows: ModelRow[],
): { cli_agents: Record<string, { traits?: TraitVector; models?: Record<string, { traits: TraitVector }> }> } {
  const cli_agents: Record<string, { traits?: TraitVector; models?: Record<string, { traits: TraitVector }> }> = {}
  for (const [cli, traits] of Object.entries(cliTraits)) cli_agents[cli] = { traits }
  for (const { cli, model, traits } of modelRows) {
    if (!model) continue
    cli_agents[cli] ??= {}
    cli_agents[cli].models ??= {}
    cli_agents[cli].models![model] = { traits }
  }
  return { cli_agents }
}

/** Candidate map ({cli, cli@model}) from edited provider traits + model rows. */
export function candidatesFromEdits(
  cliTraits: Record<string, TraitVector>,
  modelRows: ModelRow[],
): Record<string, TraitVector> {
  const out: Record<string, TraitVector> = { ...cliTraits }
  for (const { cli, model, traits } of modelRows) if (model) out[`${cli}@${model}`] = traits
  return out
}
