/**
 * Baked SPA version string (Vite injects pyproject version at build).
 * Overridable in unit tests. No secrets.
 */

let override: string | null = null

export function getBakedSpaVersion(): string {
  if (override !== null) return override
  const fromEnv = import.meta.env.VITE_SPA_VERSION
  return typeof fromEnv === 'string' ? fromEnv : ''
}

export function setBakedSpaVersionForTests(version: string | null): void {
  override = version
}
