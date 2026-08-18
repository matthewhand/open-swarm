import { test, expect } from '@playwright/test'

// Per-route smoke across mounted SPA routes (App.tsx). /builder and
// /agent-creator are unmounted (* → /) — do not list them as live surfaces.
// Backend is absent in preview, so /v1 fetch failures are tolerated — we only
// fail on pageerror.
const ROUTES = [
  '/',
  '/blueprints',
  '/chat',
  '/settings',
  '/teams',
]

for (const route of ROUTES) {
  test(`route ${route} mounts without uncaught JS errors`, async ({ page }) => {
    const jsErrors: string[] = []
    page.on('pageerror', (e) => jsErrors.push(e.message))

    await page.goto(route)

    // React mounted and rendered something (not a blank/crashed page).
    await expect(page.locator('#root')).not.toBeEmpty()
    // Persistent layout nav survives the route (proves the shell didn't crash).
    await expect(
      page.getByRole('link', { name: /Blueprints|Settings/i }).first(),
    ).toBeVisible()

    expect(
      jsErrors,
      `${route} uncaught JS errors: ${jsErrors.join(' | ')}`,
    ).toHaveLength(0)
  })
}
