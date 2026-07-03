import { test, expect } from '@playwright/test'

// Interaction test: exercises a real, backend-independent UI control — the
// navbar dark-mode toggle — and asserts that user input actually mutates app
// state (the `data-theme` attribute + the persisted localStorage value).
// Backend is absent in preview, so /v1 fetch failures are tolerated; we
// hard-fail only on UNCAUGHT JS errors (pageerror).
test('dark-mode toggle flips data-theme and persists, no uncaught JS errors', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))

  await page.goto('/')

  const root = page.locator('[data-theme]').first()
  const toggle = page.getByLabel('Toggle dark mode')

  // Default theme (no stored preference) is dark.
  await expect(root).toHaveAttribute('data-theme', 'dark')
  await expect(toggle).toBeVisible()

  // Flip to light and assert the UI state + persistence both changed.
  await toggle.click()
  await expect(root).toHaveAttribute('data-theme', 'light')
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_theme')))
    .toBe('light')

  // Flip back to dark — the control is genuinely two-way, not a one-shot.
  await toggle.click()
  await expect(root).toHaveAttribute('data-theme', 'dark')
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_theme')))
    .toBe('dark')

  expect(
    jsErrors,
    `uncaught JS errors: ${jsErrors.join(' | ')}`,
  ).toHaveLength(0)
})
