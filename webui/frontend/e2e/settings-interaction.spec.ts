import { test, expect } from '@playwright/test'

// SPA /settings page was quarantined (ADR-001). Canonical settings UI is
// Django `/settings/`. This spec only asserts the SPA shell no longer mounts
// a settings token card and that unknown paths fall through to the dashboard.
test('SPA /settings is not a mounted leftover (falls through to dashboard)', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))

  await page.goto('/settings')

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.getByPlaceholder('Paste your API token')).toHaveCount(0)

  expect(
    jsErrors,
    `uncaught JS errors: ${jsErrors.join(' | ')}`,
  ).toHaveLength(0)
})
