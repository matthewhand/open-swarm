import { test, expect } from '@playwright/test'

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
  ],
}

const ROSTERS = {
  object: 'list',
  data: [
    {
      id: 'demo-team',
      object: 'team_roster',
      name: 'Demo Team',
      description: 'Example multi-agent roster',
      members: [
        { id: 'codey', name: 'Codey', kind: 'agent', role: 'coder' },
        { id: 'stewie', name: 'Stewie', kind: 'agent', role: 'ops' },
      ],
    },
  ],
}

async function stubApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(BLUEPRINTS),
    })
  })
  await page.route('**/team_rosters.json', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ROSTERS),
    })
  })
  await page.route('**/v1/team-rosters**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ROSTERS),
    })
  })
  await page.route('**/v1/teams**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
}

test('sidepane mixes a team row; selecting it shows the unlabeled member dropdown', async ({
  page,
}) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubApis(page)
  await page.goto('/chat')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const team = list.getByRole('link', { name: /Demo Team \(team\)/ })
  await expect(team).toBeVisible()
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()

  await team.click()
  await expect(page).toHaveURL(/[?&]team=demo-team/)

  const dropdown = page.getByRole('combobox')
  await expect(dropdown).toBeVisible()
  await expect(page.getByText('Blueprint')).toHaveCount(0)
  await expect(dropdown.locator('option')).toHaveText([
    'All members',
    'Codey (agent/coder)',
    'Stewie (agent/ops)',
    'Manage Teams',
  ])
  await expect(dropdown).toHaveValue('all')
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
