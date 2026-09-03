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
      id: 'demo-council',
      object: 'team_roster',
      name: 'Demo Council',
      description: 'Example multi-agent roster',
      members: [
        { id: 'planner', name: 'Planner', kind: 'coordinator', role: 'coordinator' },
        { id: 'researcher', name: 'Researcher', kind: 'agent', role: 'researcher' },
      ],
    },
  ],
}

async function stubApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/team-rosters**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(ROSTERS),
    })
  })
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
  await page.route('**/health**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    })
  })
}

test('sidepane team row opens team thread and unlabeled member dropdown', async ({ page }) => {
  await stubApis(page)
  await page.goto('/chat')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const team = list.getByRole('link', { name: /Demo Council team/i })
  await expect(team).toBeVisible()
  await expect(team).toHaveAttribute('data-kind', 'team')
  await expect(team.getByText('Team')).toBeVisible()
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()

  await team.click()
  await expect(page).toHaveURL(/team=demo-council/)

  const select = page.getByRole('combobox', { name: 'Team members' })
  await expect(select).toBeVisible()
  await expect(page.getByText(/^Blueprint$/)).toHaveCount(0)
  const labels = await select.locator('option').allTextContents()
  expect(labels[0]).toMatch(/All members/)
  expect(labels).toContain('Planner (coordinator)')
  expect(labels[labels.length - 1]).toBe('Manage Teams')

  await select.selectOption('__manage_teams__')
  await expect(page.getByRole('dialog', { name: /Manage Teams/i })).toBeVisible()
  await expect(page).toHaveURL(/\/chat/)
})
