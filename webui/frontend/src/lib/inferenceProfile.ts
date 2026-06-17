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
