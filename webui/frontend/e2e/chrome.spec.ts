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
    {
      id: 'stewie',
      object: 'blueprint',
      name: 'Stewie',
      description: 'Helpful agent',
      abbreviation: null,
      required_mcp_servers: [],
      tags: [],
      installed: true,
      compiled: true,
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

test('Grok chrome is left rail + chat, not a top-nav product shell', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/')

  const rail = page.getByRole('navigation', { name: 'Agent list' })
  await expect(rail.getByRole('link', { name: /Support/ })).toBeVisible()
  await expect(rail.getByRole('link', { name: /Codey/ })).toBeVisible()
  await expect(rail.getByRole('link', { name: /Gate/ })).toHaveCount(0)
  await expect(rail.getByRole('link', { name: /Skeptic/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: /2 hidden/i })).toBeVisible()
  await expect(page.getByLabel('Pinned agents')).toBeVisible()
  await expect(page.getByRole('button', { name: /Plugins/i })).toBeVisible()
  await expect(page.getByLabel('Hostname')).toBeVisible()

  await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /^Home$/ })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /^Chat$/ })).toHaveCount(0)

  await expect(page.getByRole('heading', { name: 'Support' })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toHaveAttribute(
    'placeholder',
    'Message …',
  )
  await expect(page.getByRole('button', { name: 'Add' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Voice input' })).toBeVisible()
  await expect(page.getByRole('button', { name: /^Switch to (light|dark) theme$/ })).toBeVisible()
  await expect(page.getByText(/^Connected$/)).toHaveCount(0)

  const root = page.locator('[data-theme]').first()
  await expect(root).toHaveAttribute('data-theme', 'dark')
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})

test('left-rail Search opens the command palette overlay, not an in-place filter', async ({
  page,
}) => {
  await stubAgentApis(page)
  await page.goto('/chat')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await page.getByRole('searchbox', { name: 'Search' }).click()
  const palette = page.getByRole('dialog', { name: 'Search' })
  await expect(palette).toBeVisible()
  await expect(palette.getByRole('combobox', { name: 'Search' })).toHaveAttribute(
    'placeholder',
    'Search',
  )
  await expect(palette.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true')
  for (const tab of ['Messages', 'Bots', 'Groups', 'Files', 'Links', 'Routines', 'Actions']) {
    await expect(palette.getByRole('tab', { name: tab })).toBeVisible()
  }
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await page.keyboard.press('Escape')
  await expect(palette).toHaveCount(0)
})

test('legacy /agents lands on chat chrome with query', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/agents?blueprint=codey')
  await expect(page).toHaveURL(/\/chat\/?\?blueprint=codey/)
  await expect(page.getByRole('textbox', { name: 'Chat message' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0)
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})

test('chat header Computer control icon opens a WIP modal (REQ-27b)', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/chat')

  const tools = page.getByRole('toolbar', { name: 'Chat tools' })
  const trigger = page.getByRole('button', { name: 'Computer control' })
  await expect(tools).toBeVisible()
  await expect(trigger).toBeVisible()

  await trigger.click()
  const dialog = page.getByRole('dialog', { name: 'Computer control' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('WIP', { exact: true })).toBeVisible()
  await expect(dialog).toContainText(
    'Computer control will use a placed OMB or Rakazo remote; not implemented here.',
  )
  await expect(dialog.getByRole('checkbox')).toHaveCount(0)
  await expect(dialog.getByRole('switch')).toHaveCount(0)

  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})

test('right-click hide from sidebar persists across reload; unhide restores', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/chat')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const codey = list.getByRole('link', { name: /Codey/ })
  await expect(codey).toBeVisible()
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await codey.click({ button: 'right' })
  await page.getByRole('menuitem', { name: /Hide from sidebar/i }).click()
  await expect(list.getByRole('link', { name: /Codey/ })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hidden_agents')))
    .toBe(JSON.stringify(['gate', 'skeptic', 'codey']))

  await page.reload()
  await expect(list.getByRole('link', { name: /Codey/ })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Stewie/ })).toBeVisible()

  await page.getByRole('button', { name: /3 hidden/i }).click()
  await expect(page.getByRole('dialog', { name: /Hidden agents/i })).toBeVisible()
  await page.getByRole('button', { name: /Unhide Codey/i }).click()
  await expect(page.getByRole('button', { name: /2 hidden/i })).toBeVisible()
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})

async function html5Drag(
  source: import('@playwright/test').Locator,
  target: import('@playwright/test').Locator,
  phase: 'highlight' | 'drop' | 'full' = 'full',
) {
  await source.evaluate((el) => {
    el.dispatchEvent(
      new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: new DataTransfer() }),
    )
  })
  if (phase === 'highlight' || phase === 'full') {
    await target.evaluate((el) => {
      const dt = new DataTransfer()
      el.dispatchEvent(new DragEvent('dragenter', { bubbles: true, cancelable: true, dataTransfer: dt }))
      el.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }))
    })
  }
  if (phase === 'drop' || phase === 'full') {
    await target.evaluate((el) => {
      el.dispatchEvent(
        new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: new DataTransfer() }),
      )
    })
    // Hide unmounts the source row; dragend is best-effort.
    if ((await source.count()) > 0) {
      await source.evaluate((el) => {
        el.dispatchEvent(
          new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: new DataTransfer() }),
        )
      })
    }
  }
}

test('drag any rail row onto Hidden, including Support; Unhide restores; no Hide-all', async ({
  page,
}) => {
  await stubAgentApis(page)
  await page.goto('/chat')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const zone = page.getByRole('region', { name: 'Hidden' })
  // REQ-26 first load already seeded gate + skeptic.
  await expect(page.getByRole('button', { name: /2 hidden/i })).toBeVisible()
  await expect(page.getByRole('button', { name: /Hide all/i })).toHaveCount(0)

  const support = list.getByRole('link', { name: /Support/ })
  await html5Drag(support, zone, 'highlight')
  await expect(zone).toHaveAttribute('data-drag-over', 'true')
  await html5Drag(support, zone, 'drop')
  await expect(list.getByRole('link', { name: /Support/ })).toHaveCount(0)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hidden_agents')))
    .toBe(JSON.stringify(['gate', 'skeptic', 'support']))

  const codey = list.getByRole('link', { name: /Codey/ })
  await html5Drag(codey, zone)
  await expect(list.getByRole('link', { name: /Codey/ })).toHaveCount(0)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hidden_agents')))
    .toBe(JSON.stringify(['gate', 'skeptic', 'support', 'codey']))

  await expect(page.getByRole('button', { name: /4 hidden/i })).toBeVisible()
  await expect(page.getByRole('button', { name: /Hide all/i })).toHaveCount(0)
  await page.getByRole('button', { name: /4 hidden/i }).click()
  const dialog = page.getByRole('dialog', { name: /Hidden agents/i })
  await dialog.getByRole('button', { name: /Unhide Support/i }).click()
  await dialog.getByRole('button', { name: /Unhide Codey/i }).click()
  await expect(list.getByRole('link', { name: /Support/ })).toBeVisible()
  await expect(list.getByRole('link', { name: /Codey/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /2 hidden/i })).toBeVisible()
})

test('first load seeds Hidden with gate and skeptic; Unhide persists', async ({ page }) => {
  await stubAgentApis(page)
  await page.goto('/')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  await expect(list.getByRole('link', { name: /Support/ })).toBeVisible()
  await expect(list.getByRole('link', { name: /Gate/ })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Skeptic/ })).toHaveCount(0)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hidden_agents')))
    .toBe(JSON.stringify(['gate', 'skeptic']))

  await page.getByRole('button', { name: /2 hidden/i }).click()
  const dialog = page.getByRole('dialog', { name: /Hidden agents/i })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: /Unhide Gate/i }).click()
  await expect(list.getByRole('link', { name: /Gate/ })).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('swarm_hidden_agents')))
    .toBe(JSON.stringify(['skeptic']))

  await page.reload()
  await expect(list.getByRole('link', { name: /Gate/ })).toBeVisible()
  await expect(list.getByRole('link', { name: /Skeptic/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: /1 hidden/i })).toBeVisible()
})

test('hover-edit on a role agent opens the modal-end Blueprint editor', async ({ page }) => {
  const jsErrors: string[] = []
  page.on('pageerror', (e) => jsErrors.push(e.message))
  await stubAgentApis(page)
  await page.goto('/')

  const list = page.getByRole('navigation', { name: 'Agent list' })
  const support = list.getByRole('link', { name: /Support/ })
  await expect(support).toBeVisible()
  // REQ-26 seeds gate/skeptic as Hidden on first load; Support stays visible.
  await expect(list.getByRole('link', { name: /Gate/ })).toHaveCount(0)
  await expect(list.getByRole('link', { name: /Skeptic/ })).toHaveCount(0)

  await support.hover()
  const edit = page.getByRole('button', { name: 'Edit Support blueprint' })
  await expect(edit).toBeVisible()
  await edit.click()

  const sheet = page.getByRole('dialog', { name: 'Settings' })
  await expect(sheet).toBeVisible()
  await expect(sheet).toHaveClass(/modal-end/)
  await expect(sheet.getByRole('heading', { name: 'Blueprint' })).toBeVisible()
  await expect(sheet.locator('.os-code-python')).toContainText('Socratic')
  await expect(page.getByRole('dialog', { name: /Teams/i })).toHaveCount(0)
  expect(jsErrors, `uncaught JS errors: ${jsErrors.join(' | ')}`).toHaveLength(0)
})
