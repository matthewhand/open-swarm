/**
 * Settings System helpers (REQ-56).
 *
 * Size labels stay human-readable. Missing or empty store is
 * "not created yet" — never a traceback or a framework name.
 */

export function formatStoreSize(bytes: number | null | undefined): string {
  if (bytes == null || !Number.isFinite(Number(bytes)) || Number(bytes) <= 0) {
    return 'not created yet'
  }
  let value = Number(bytes)
  const units = ['B', 'KB', 'MB', 'GB'] as const
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  if (units[unit] === 'B') return `${Math.round(value)} B`
  return `${value.toFixed(1)} ${units[unit]}`
}