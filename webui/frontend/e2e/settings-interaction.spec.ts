import { test, expect } from '@playwright/test'

// Interaction test on the Settings page — the show/hide API-token control.
// This card renders unconditionally (it does not depend on any /v1 query), so
// it works in the backendless preview build. We assert the toggle actually
// changes the input's masking (type password<->text) and its own aria-label,
// both ways, with no uncaught JS errors.
test('settings show/hide token toggles input masking, no uncaught JS errors', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))

  await page.goto('/settings')

  const tokenInput = page.getByPlaceholder('Paste your API token')
  await expect(tokenInput).toBeVisible()

  // Masked by default.
  await expect(tokenInput).toHaveAttribute('type', 'password')
  const showBtn = page.getByRole('button', { name: 'Show token' })
  await expect(showBtn).toBeVisible()

  // Reveal: input unmasks and the control relabels to its inverse action.
  await showBtn.click()
  await expect(tokenInput).toHaveAttribute('type', 'text')
  await expect(page.getByRole('button', { name: 'Hide token' })).toBeVisible()

  // Re-hide: genuinely two-way, returns to masked.
  await page.getByRole('button', { name: 'Hide token' }).click()
  await expect(tokenInput).toHaveAttribute('type', 'password')
  await expect(page.getByRole('button', { name: 'Show token' })).toBeVisible()

  expect(
    jsErrors,
    `uncaught JS errors: ${jsErrors.join(' | ')}`,
  ).toHaveLength(0)
})
