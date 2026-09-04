import { test, expect } from '@playwright/test'

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

const BLUEPRINTS = {
  object: 'list',
  data: [
    {
      id: 'cli_agent',
      object: 'blueprint',
      name: 'CLI agent',
      description: 'CLI',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
    },
  ],
}

function shotPath(testInfo: { outputDir: string }, name: string): string {
  const root = process.env.ARTIFACTS_DIR || testInfo.outputDir
  return `${root}/${name}`
}

test('team dropdown change is a centred status line and survives reload', async ({
  page,
}, testInfo) => {
  const stored: { role: string; content: string }[] = []
  await page.route('**/chat/thread**', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as {
        message?: { role?: string; content?: string }
      }
      if (body.message?.role && body.message.content) {
        stored.push({ role: body.message.role, content: body.message.content })
      }
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        agent_id: 'team-demo-team',
        conversation_id: 'team-demo-team',
        messages: stored,
      }),
    })
  })
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
  await page.route('**/v1/cli-agents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ clis: ['antigravity', 'grok'] }),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        object: 'list',
        data: [{ id: 'grok-4', object: 'model', created: 0, owned_by: 'xai' }],
      }),
    })
  })

  await page.goto('/chat?team=demo-team')
  const teamSelect = page.getByRole('combobox', { name: 'Team members' })
  await expect(teamSelect).toHaveValue('all')
  await page.screenshot({
    path: shotPath(testInfo, 'team_dropdown_before.png'),
    fullPage: true,
  })

  await teamSelect.selectOption('codey')
  const status = page.getByTestId('chat-status')
  await expect(status).toHaveCount(1)
  await expect(status).toHaveText('Team target: All members → Codey (agent/coder)')
  await expect(status).toHaveClass(/os-chat-status/)
  await expect(status).not.toHaveClass(/chat-start|chat-end/)
  await expect(status.locator('.chat-bubble')).toHaveCount(0)
  await page.screenshot({
    path: shotPath(testInfo, 'team_dropdown_status_line.png'),
    fullPage: true,
  })

  await page.reload()
  await expect(page.getByTestId('chat-status')).toHaveCount(1)
  await expect(page.getByTestId('chat-status')).toHaveText(
    'Team target: All members → Codey (agent/coder)',
  )
  await expect(page.getByTestId('chat-status')).not.toHaveClass(/chat-start|chat-end/)
})

test('CLI dropdown change is one bubble-less status line', async ({ page }, testInfo) => {
  await page.route('**/chat/thread**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ agent_id: 'cli_agent', conversation_id: 'x', messages: [] }),
    })
  })
  await page.route('**/v1/blueprints**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(BLUEPRINTS),
    })
  })
  await page.route('**/v1/cli-agents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ clis: ['antigravity', 'grok'] }),
    })
  })
  await page.route('**/v1/models**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ object: 'list', data: [] }),
    })
  })

  await page.goto('/chat?blueprint=cli_agent&mode=cli&cli=antigravity')
  const cli = page.getByRole('combobox', { name: 'CLI' })
  await expect(cli).toHaveValue('antigravity')
  await cli.selectOption('grok')
  const status = page.getByTestId('chat-status')
  await expect(status).toHaveCount(1)
  await expect(status).toHaveText('CLI: antigravity → grok')
  await expect(status).not.toHaveClass(/chat-start|chat-end/)
  await page.screenshot({
    path: shotPath(testInfo, 'cli_dropdown_status_line.png'),
    fullPage: true,
  })
})
