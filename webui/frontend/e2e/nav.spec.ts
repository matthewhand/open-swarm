import { test, expect } from '@playwright/test'

// Per-route smoke across mounted SPA routes only (ADR-001: `/` + `/chat`).
// Bare /teams|/blueprints|/settings|/builder|/agent-creator are not SPA
// surfaces — Django RedirectView owns them in production; SPA `*` → `/`.
// Backend is absent in preview, so /v1 fetch failures are tolerated — we only
// fail on pageerror.
const ROUTES = ['/', '/chat']

for (const route of ROUTES) {
  test(`route ${route} mounts without uncaught JS errors`, async ({ page }) => {
    const jsErrors: string[] = []
    page.on('pageerror', (e) => jsErrors.push(e.message))

    await page.goto(route)

    await expect(page.locator('#root')).not.toBeEmpty()
    await expect(
      page.getByRole('navigation', { name: 'Primary' }),
    ).toBeVisible()

    expect(
      jsErrors,
      `${route} uncaught JS errors: ${jsErrors.join(' | ')}`,
    ).toHaveLength(0)
  })
}

test('unknown SPA path falls through to dashboard (no leftover shells)', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  // A path with no proxy, no Django route, and no SPA route: the React
  // catch-all must land on the dashboard. (/teams is NOT such a path —
  // production Django redirects it to the teams UI.)
  await page.goto('/definitely-not-a-real-path')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  expect(jsErrors).toHaveLength(0)
})
