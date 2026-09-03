import { test, expect } from '@playwright/test'

// Per-route smoke across mounted SPA routes only (ADR-001: `/` + `/chat`).
// Product chrome is left rail + chat. Django operator pages stay on trailing-slash
// routes and are reachable from the composer + menu.
const ROUTES = ['/', '/chat']

for (const route of ROUTES) {
  test(`route ${route} mounts without uncaught JS errors`, async ({ page }) => {
    const jsErrors: string[] = []
    page.on('pageerror', (e) => jsErrors.push(e.message))

    await page.goto(route)

    await expect(page.locator('#root')).not.toBeEmpty()
    await expect(page.getByRole('navigation', { name: 'Agent list' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()

    expect(
      jsErrors,
      `${route} uncaught JS errors: ${jsErrors.join(' | ')}`,
    ).toHaveLength(0)
  })
}

test('unknown SPA path falls through to chat (no leftover shells)', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await page.goto('/definitely-not-a-real-path')
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toHaveCount(0)
  expect(jsErrors).toHaveLength(0)
})
