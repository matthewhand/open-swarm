import { writeFileSync } from 'node:fs'
import { test, expect } from '@playwright/test'

test('Rail avatar theme lists a disabled 3D robot coming-soon option', async ({ page }) => {
  await page.route('**/v1/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [], configured: [], kinds: [], profiles: [] }),
    })
  })
  await page.goto('/chat')
  await page.getByRole('button', { name: 'Open settings' }).click()
  const dialog = page.getByRole('dialog', { name: 'Settings' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Rail' }).click()

  const picker = page.getByLabel('Avatar theme')
  await expect(picker).toBeVisible()
  await expect(picker).toHaveValue('blobs')

  const robot3d = page.locator('#os-avatar-theme option[value="robot3d"]')
  await expect(robot3d).toHaveText('3D robot (coming soon)')
  await expect(robot3d).toBeDisabled()
  const adr = page.getByRole('link', { name: '3D robot (ADR-008)' })
  await expect(adr).toBeVisible()
  await expect(adr).toHaveAttribute(
    'href',
    'https://github.com/matthewhand/open-swarm/blob/main/docs/adr/008-3d-robot-avatar-theme.md',
  )
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_avatar_theme')))
    .toBeNull()

  const optionDump = await page.locator('#os-avatar-theme option').evaluateAll((nodes) =>
    nodes.map((node) => {
      const option = node as HTMLOptionElement
      return {
        value: option.value,
        label: option.textContent?.trim(),
        disabled: option.disabled,
      }
    }),
  )
  writeFileSync(
    '/opt/cursor/artifacts/avatar_theme_robot3d_options.json',
    `${JSON.stringify(optionDump, null, 2)}\n`,
  )

  await dialog.locator('.pt-2').screenshot({
    path: '/opt/cursor/artifacts/avatar_theme_robot3d_picker_rail.png',
  })
})
