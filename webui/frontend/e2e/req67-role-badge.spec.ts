import { test, expect } from '@playwright/test'

const ROLE_ACCENT_COLORS = ['#3d8f8a', '#c47a3a', '#7a6b9b', '#4f8ec9', '#c9a227', '#8a5a9b']

const BLUEPRINTS = {
  object: 'list',
  data: [
    {
      id: 'codey',
      object: 'blueprint',
      name: 'Codey',
      description: 'Code assistant',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
    },
    {
      id: 'cos',
      object: 'blueprint',
      name: 'Pat',
      description: 'Talks to any team.',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
      role: 'chief_of_staff',
    },
  ],
}

async function stubAgentApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(BLUEPRINTS),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/v1/team-rosters**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
  await page.route('**/v1/herdr-agents**', async (route) => {
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

function assertNoRoleAccent(boxShadow: string, background: string, outline: string) {
  const chrome = `${boxShadow} ${background} ${outline}`.toLowerCase()
  for (const color of ROLE_ACCENT_COLORS) {
    expect(chrome, `row chrome should not use role colour ${color}`).not.toContain(color)
  }
}

test('REQ-67: role colour is the badge only; selected/hover stay', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('swarm_hidden_agents', '[]')
  })
  await stubAgentApis(page)
  await page.goto('/chat?blueprint=codey')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const support = list.getByRole('link', { name: /Support/ })
  const gate = list.getByRole('link', { name: /Gate/ })
  const skeptic = list.getByRole('link', { name: /Skeptic/ })
  const cos = list.getByRole('link', { name: /Pat/ })
  const codey = list.getByRole('link', { name: /Codey/ })

  await expect(support).toBeVisible()
  await expect(gate).toBeVisible()
  await expect(skeptic).toBeVisible()
  await expect(cos).toBeVisible()
  await expect(codey).toBeVisible()

  for (const row of [support, gate, skeptic, cos, codey]) {
    await expect(row).toHaveClass(/os-agent-row/)
    await expect(row).not.toHaveClass(/os-agent-row--(support|gate|skeptic|cos|chief_of_staff)/)
    await expect(row).not.toHaveClass(/os-agent-role-/)
    const styles = await row.evaluate((el) => {
      const computed = getComputedStyle(el)
      return {
        boxShadow: computed.boxShadow,
        background: computed.backgroundColor,
        outline: computed.outlineColor,
      }
    })
    assertNoRoleAccent(styles.boxShadow, styles.background, styles.outline)
  }

  await expect(support.locator('.os-agent-role-badge')).toHaveAttribute('data-role', 'support')
  await expect(gate.locator('.os-agent-role-badge')).toHaveAttribute('data-role', 'gate')
  await expect(skeptic.locator('.os-agent-role-badge')).toHaveAttribute('data-role', 'skeptic')
  await expect(cos.locator('.os-agent-role-badge')).toHaveAttribute('data-role', 'chief_of_staff')
  await expect(codey.locator('.os-agent-role-badge')).toHaveCount(0)

  const supportBadgeColor = await support.locator('.os-agent-role-badge').evaluate((el) => {
    return getComputedStyle(el).color
  })
  expect(supportBadgeColor).toBe('rgb(61, 143, 138)') // #3d8f8a

  await expect(codey).toHaveClass(/os-agent-row--active/)
  await expect(support).not.toHaveClass(/os-agent-row--active/)

  const idleBg = await support.evaluate((el) => getComputedStyle(el).backgroundColor)
  await support.hover()
  const hoverBg = await support.evaluate((el) => getComputedStyle(el).backgroundColor)
  expect(hoverBg).not.toBe(idleBg)
  const hoverChrome = await support.evaluate((el) => {
    const computed = getComputedStyle(el)
    return `${computed.boxShadow} ${computed.backgroundColor}`
  })
  for (const color of ROLE_ACCENT_COLORS) {
    expect(hoverChrome.toLowerCase()).not.toContain(color)
  }
})
