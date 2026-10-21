import { chromium, expect, test } from '@playwright/test'

const endpoint = process.env.SWARM_DEVICE_CDP_URL
const target = process.env.SWARM_DEVICE_TEST_URL

test('physical browser keeps compact, expanded and focused composer inside its visible viewport', async ({}, info) => {
  test.skip(!endpoint || !target, 'Set SWARM_DEVICE_CDP_URL and SWARM_DEVICE_TEST_URL for an explicitly selected test tab')
  const browser = await chromium.connectOverCDP(endpoint!)
  const page = browser.contexts().flatMap(context => context.pages()).find(page => page.url() === target)
  const testDraft = 'Physical device layout check\nSecond line'
  let originalDraft: string | undefined
  try {
    expect(page, 'Open the intended test URL on the device first').toBeDefined()
    const input = page!.getByRole('textbox', { name: 'Chat message' })
    originalDraft = await input.inputValue()
    await page!.bringToFront()
    await page!.reload()
    const toggle = page!.getByRole('button', { name: 'Context window usage' })
    await expect(toggle).toHaveAttribute('aria-expanded', 'false')
    const measure = () => page!.evaluate(() => {
      const send = document.querySelector('.os-composer__send')!.getBoundingClientRect()
      const input = document.querySelector('textarea[aria-label="Chat message"]')!.getBoundingClientRect()
      const log = document.querySelector('[role="log"]')!
      return { width: innerWidth, height: visualViewport!.height, dpr: devicePixelRatio,
        pageOverflow: document.documentElement.scrollWidth - innerWidth,
        conversationOverflow: log.scrollWidth - log.clientWidth,
        sendBottom: send.bottom - visualViewport!.offsetTop, inputBottom: input.bottom - visualViewport!.offsetTop }
    })
    const check = async () => {
      await expect.poll(async () => {
        const result = await measure()
        return Math.max(result.pageOverflow, result.conversationOverflow, result.sendBottom - result.height, result.inputBottom - result.height)
      }).toBeLessThanOrEqual(1)
      return measure()
    }
    const compact = await check()
    await page!.screenshot({ path: info.outputPath('compact.png') })
    await toggle.click()
    await expect(page!.getByRole('region', { name: 'Token usage details' })).toBeVisible()
    const expanded = await check()
    await page!.screenshot({ path: info.outputPath('expanded.png') })
    await toggle.click()
    await input.click()
    await input.fill(testDraft)
    const focused = await check()
    const softKeyboardObserved = compact.height - focused.height > 100
    if (process.env.SWARM_DEVICE_EXPECT_SOFT_KEYBOARD === '1') expect(softKeyboardObserved).toBe(true)
    await page!.screenshot({ path: info.outputPath('focused.png') })
    await info.attach('device-layout', { body: JSON.stringify({ compact, expanded, focused, softKeyboardObserved }, null, 2), contentType: 'application/json' })
  } finally {
    if (page && originalDraft !== undefined && !page.isClosed()) {
      const input = page.getByRole('textbox', { name: 'Chat message' })
      if (await input.inputValue() === testDraft) await input.fill(originalDraft)
    }
    // connectOverCDP disconnects its transport; it does not own the device's Chrome.
    await browser.close()
  }
})
