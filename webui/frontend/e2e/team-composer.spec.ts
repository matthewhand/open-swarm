import { test, expect } from '@playwright/test'

const AGENTS = {
  object: 'list',
  data: [
    { id: 'jeeves', name: 'Jeeves', kind: 'api', source: 'blueprint:jeeves', placeholder: false },
    { id: 'grok', name: 'grok', kind: 'cli', source: 'cli:grok', placeholder: false },
    {
      id: 'acp',
      name: 'ACP harness',
      kind: 'remote',
      source: 'placeholder:remote:acp',
      placeholder: true,
    },
  ],
}

async function stubComposerApis(page: import('@playwright/test').Page) {
  await page.route('**/v1/team-agents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(AGENTS),
    })
  })
  await page.route('**/v1/team-rosters**', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON()
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'research-squad',
          object: 'team_roster',
          name: body?.name ?? 'research-squad',
          members: body?.members ?? [],
          wires: body?.wires ?? { handoff: true, as_tool: true },
        }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })
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

test(' + opens two-pane team composer; add/remove and save roster', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubComposerApis(page)
  await page.goto('/')

  const primary = page.getByRole('navigation', { name: 'Primary' })
  await expect(primary.getByRole('link', { name: 'Home' })).toBeVisible()
  await expect(primary.getByRole('link', { name: 'Chat' })).toBeVisible()
  // Existing Django Teams href is fine; there must be no SPA /teams tab.
  await expect(primary.getByRole('link', { name: 'Teams', exact: true })).toHaveAttribute(
    'href',
    '/teams/launch/',
  )

  await page.getByRole('button', { name: 'Compose team' }).click()
  await expect(page.getByRole('heading', { name: /new team/i })).toBeVisible()

  const drop = page.getByTestId('team-drop-zone')
  await expect(drop).toBeVisible()
  await expect(drop).toHaveText(/drop agents here/i)

  const available = page.getByRole('list', { name: /available agents list/i })
  await expect(available.getByText('Jeeves')).toBeVisible()
  await expect(available.getByText('API').first()).toBeVisible()
  await expect(available.getByText('CLI').first()).toBeVisible()
  await expect(available.getByText('remote').first()).toBeVisible()

  await expect(page.getByRole('checkbox', { name: /handoff/i })).toBeChecked()
  await expect(page.getByRole('checkbox', { name: /as_tool/i })).toBeChecked()
  await expect(page.getByText(/gate is unwired/i)).toBeVisible()

  await available.getByRole('button', { name: 'Add' }).first().click()
  const roster = page.getByRole('list', { name: /roster members/i })
  await expect(roster.getByText('jeeves')).toBeVisible()
  await expect(roster.getByText('API')).toBeVisible()

  await page.getByLabel(/team name/i).fill('research-squad')
  await page.getByRole('button', { name: /save roster/i }).click()
  await expect(page.getByRole('status')).toContainText(/team_rosters\.json/i)

  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
