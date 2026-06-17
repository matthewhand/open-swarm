// Full-ruleset accessibility audit (WCAG2 A/AA + best-practice).
// Walks every route in both light and dark themes, injects axe-core into the
// live page, runs the COMPLETE ruleset (no runOnly filter), and prints every
// violation verbatim. Exit 1 if any violation is found.
//
// Run:  node scripts/a11y-audit.mjs [baseUrl]
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const axePath = require.resolve('axe-core/axe.min.js')
const axeSource = readFileSync(axePath, 'utf8')

const BASE = process.argv[2] || 'http://127.0.0.1:8011'
const ROUTES = ['/', '/chat', '/teams', '/blueprints', '/builder', '/agent-creator', '/settings']
const THEMES = ['light', 'dark']
const VIEWPORTS = [
  { name: 'desktop', width: 1280, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]

const consoleErrors = []
let totalViolations = 0

const browser = await chromium.launch()
for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } })
  const page = await ctx.newPage()
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(`[${vp.name}] ${m.text()}`)
  })
  page.on('pageerror', (e) => consoleErrors.push(`[${vp.name}] pageerror: ${e.message}`))

  for (const theme of THEMES) {
    for (const route of ROUTES) {
      const url = `${BASE}${route}`
      await page.goto(url, { waitUntil: 'networkidle' }).catch(() => {})
      // App stores theme on a data-theme attr toggled by a checkbox; force it.
      await page.evaluate((t) => {
        localStorage.setItem('swarm_theme', t)
        document.querySelectorAll('[data-theme]').forEach((el) => el.setAttribute('data-theme', t))
      }, theme)
      await page.waitForTimeout(150)
      await page.addScriptTag({ content: axeSource })
      const result = await page.evaluate(async () => await window.axe.run(document))
      const tag = `${vp.name}/${theme}${route}`
      if (result.violations.length === 0) {
        console.log(`  PASS  ${tag}`)
      } else {
        totalViolations += result.violations.length
        console.log(`  FAIL  ${tag}  (${result.violations.length})`)
        for (const v of result.violations) {
          console.log(`        • [${v.impact}] ${v.id}: ${v.help}`)
          for (const n of v.nodes.slice(0, 3)) {
            console.log(`            ${n.target.join(' ')}`)
          }
        }
      }
    }
  }
  await ctx.close()
}
await browser.close()

console.log('\n' + '='.repeat(70))
console.log(`Total axe violations: ${totalViolations}`)
const uniqErrors = [...new Set(consoleErrors)]
console.log(`Console errors: ${uniqErrors.length}`)
for (const e of uniqErrors) console.log(`  • ${e}`)
console.log('='.repeat(70))
process.exit(totalViolations === 0 ? 0 : 1)
