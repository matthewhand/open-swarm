import { test, expect } from '@playwright/test'

// Interaction test: exercises a real, backend-independent UI control — the
// navbar theme toggle — and asserts that user input actually mutates app
// state (the `data-theme` attribute + the persisted localStorage value).
// Backend is absent in preview, so /v1 fetch failures are tolerated; we
// hard-fail only on UNCAUGHT JS errors (pageerror).
test('theme toggle flips data-theme and persists, no uncaught JS errors', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))

  await page.goto('/')

  const root = page.locator('[data-theme]').first()
  // Accessible name flips with state ("Switch to light/system/dark theme").
  const toggle = page.getByRole('button', { name: /^Switch to (light|dark|system) theme$/ })

  // Default theme (no stored preference) is dark, matching Django pages.
  await expect(root).toHaveAttribute('data-theme', 'dark')
  await expect(toggle).toBeVisible()
  await expect(toggle).not.toHaveText(/Light|Dark/)

  // Flip to light and assert the UI state + persistence both changed.
  await toggle.click()
  await expect(root).toHaveAttribute('data-theme', 'light')
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_theme')))
    .toBe('light')

  // Flip to system — stores 'system' and resolves data-theme to light or dark (never 'system').
  await toggle.click()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_theme')))
    .toBe('system')
  const resolvedAttr = await root.getAttribute('data-theme')
  expect(['light', 'dark']).toContain(resolvedAttr)

  // Flip back to dark — complete 3-way cycle.
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

test('stored theme preference is restored on reload', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('swarm_theme', 'light'))
  await page.goto('/')

  const root = page.locator('[data-theme]').first()
  await expect(root).toHaveAttribute('data-theme', 'light')
})

test('stored system theme preference resolves to light or dark on reload', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('swarm_theme', 'system'))
  await page.goto('/')

  const root = page.locator('[data-theme]').first()
  const theme = await root.getAttribute('data-theme')
  expect(['light', 'dark']).toContain(theme)
  expect(theme).not.toBe('system')
})
