// Capture full-page screenshots of key routes in light + dark for visual review.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.argv[2] || 'http://127.0.0.1:8011'
const OUT = process.argv[3] || '/tmp/swarm_shots'
mkdirSync(OUT, { recursive: true })
const ROUTES = [['/', 'dashboard'], ['/blueprints', 'blueprints'], ['/builder', 'builder'], ['/chat', 'chat']]
const THEMES = ['light', 'dark']

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
const page = await ctx.newPage()
for (const theme of THEMES) {
  for (const [route, name] of ROUTES) {
    await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle' }).catch(() => {})
    await page.evaluate((t) => {
      localStorage.setItem('swarm_theme', t)
      document.querySelectorAll('[data-theme]').forEach((el) => el.setAttribute('data-theme', t))
    }, theme)
    await page.waitForTimeout(250)
    const file = `${OUT}/${name}-${theme}.png`
    await page.screenshot({ path: file, fullPage: true })
    console.log(file)
  }
}
await browser.close()
