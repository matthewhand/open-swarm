import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const ARTIFACTS = '/opt/cursor/artifacts'

async function stubApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/v1/teams**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/health**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    })
  })
}

test('Bee theme is opt-in and paints both locked variants', async ({ page }) => {
  fs.mkdirSync(ARTIFACTS, { recursive: true })
  await stubApis(page)
  await page.goto('/chat')

  await expect(page.getByRole('button', { name: 'Open settings' })).toBeVisible()
  await expect(page.locator('svg[data-avatar-theme="blobs"]').first()).toBeAttached()
  await expect(page.locator('svg[data-avatar-theme="bee"]')).toHaveCount(0)
  await page.screenshot({
    path: path.join(ARTIFACTS, 'bee_theme_default_still_blobs.png'),
    fullPage: true,
  })

  await page.getByRole('button', { name: 'Open settings' }).click()
  const dialog = page.getByRole('dialog', { name: 'Settings' })
  await expect(dialog).toBeVisible()
  await page.getByRole('button', { name: 'Rail' }).click()
  const picker = page.getByLabel('Avatar theme')
  await expect(picker).toHaveValue('blobs')
  await expect(picker.locator('option')).toHaveText(['Default', 'Blobs', 'Bee'])
  await expect(dialog.getByText(/optional choices/i)).toBeVisible()
  await expect(dialog.getByText(/never auto-applied/i)).toBeVisible()
  await page.screenshot({
    path: path.join(ARTIFACTS, 'bee_theme_settings_picker.png'),
  })

  await picker.selectOption('bee')
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_avatar_theme')))
    .toBe('bee')

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()

  await expect(page.locator('svg[data-avatar-theme="bee"]').first()).toBeAttached()
  await expect(page.locator('svg[data-bee-variant="side-on"]').first()).toBeAttached()
  await expect(page.locator('svg[data-bee-variant="face-only"]').first()).toBeAttached()
  await expect(page.locator('[data-googly="true"]').first()).toBeAttached()
  await page.screenshot({
    path: path.join(ARTIFACTS, 'bee_theme_rail_both_variants.png'),
    fullPage: true,
  })
})
