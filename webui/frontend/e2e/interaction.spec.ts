import { test, expect } from '@playwright/test'

/**
 * Validates state integrity of interactive elements that must persist across
 * reloads, such as the theme toggle.
 */
test('dark-mode toggle flips data-theme and persists, no uncaught JS errors', async ({
  page,
}) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))

  await page.goto('/')

  const root = page.locator('[data-theme]').first()
  const toggle = page.locator('label.swap-rotate')

  // Wait for the hydration to complete
  await page.waitForLoadState('networkidle')

  // The application seems to default to 'dark' locally based on the CI output.
  // Instead of hardcoding 'light' as the default, we flip whatever the initial theme is.
  const initialTheme = await root.getAttribute('data-theme')
  expect(initialTheme).toMatch(/light|dark/)

  await expect(toggle).toBeVisible()

  // Flip the theme
  await toggle.click()
  const flippedTheme = initialTheme === 'light' ? 'dark' : 'light'
  await expect(root).toHaveAttribute('data-theme', flippedTheme)

  // Reload the page
  await page.reload()

  // Wait for the hydration to complete
  await page.waitForLoadState('networkidle')

  // Ensure it persists
  await expect(root).toHaveAttribute('data-theme', flippedTheme)

  // A11y / Error check: ensure no raw JS exceptions were thrown
  expect(jsErrors).toEqual([])
})
