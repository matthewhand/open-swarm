// Render terminal-style PNG "screenshots" from captured command output.
// Reads a JSON manifest [{ name, title, lines: [..] }] and writes one PNG per
// entry to the output dir. Uses playwright (already a dev dep) — no terminal
// capture binary needed. Light ANSI-ish coloring is applied by simple rules so
// PASS/headings/prompts read clearly.
import { chromium } from 'playwright'
import { readFileSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

const manifest = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const outDir = process.argv[3] || '/tmp/term'
mkdirSync(outDir, { recursive: true })

const esc = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// Color a line by lightweight heuristics (matches our proof/CLI output).
function colorize(line) {
  const h = esc(line)
  if (/\bPASS\b/.test(line)) return h.replace(/PASS/g, '<span class="g">PASS</span>')
  if (/\bFAIL\b|\bERR\b/.test(line)) return h.replace(/FAIL|ERR/g, '<span class="r">$&</span>')
  if (/^\s*[#=]{2,}/.test(line) || /^#\s/.test(line)) return `<span class="b">${h}</span>`
  if (/^\$ /.test(line)) return `<span class="c">${h}</span>`
  if (/^\s*(SKILL|PERMUTATION|AGENT)\b/.test(line)) return `<span class="dim">${h}</span>`
  return h
}

function html(title, lines) {
  const body = lines.map(colorize).join('\n')
  return `<!doctype html><html><head><meta charset="utf8"><style>
    *{margin:0;box-sizing:border-box}
    body{background:#0d1117;padding:28px;display:inline-block}
    .win{background:#161b22;border:1px solid #30363d;border-radius:10px;
      box-shadow:0 16px 48px rgba(0,0,0,.5);overflow:hidden;width:920px}
    .bar{background:#21262d;padding:10px 14px;display:flex;align-items:center;gap:8px;
      border-bottom:1px solid #30363d}
    .dot{width:12px;height:12px;border-radius:50%}
    .d1{background:#ff5f56}.d2{background:#ffbd2e}.d3{background:#27c93f}
    .ttl{color:#8b949e;font:600 12px/1 ui-monospace,Menlo,monospace;margin-left:10px}
    pre{margin:0;padding:18px 20px;color:#c9d1d9;
      font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}
    .g{color:#3fb950;font-weight:700}.r{color:#f85149;font-weight:700}
    .b{color:#58a6ff;font-weight:700}.c{color:#d2a8ff}.dim{color:#8b949e}
  </style></head><body><div class="win">
    <div class="bar"><span class="dot d1"></span><span class="dot d2"></span>
      <span class="dot d3"></span><span class="ttl">${esc(title)}</span></div>
    <pre>${body}</pre></div></body></html>`
}

const browser = await chromium.launch()
const page = await browser.newPage({ deviceScaleFactor: 2 })
for (const { name, title, lines } of manifest) {
  await page.setContent(html(title, lines), { waitUntil: 'networkidle' })
  const el = await page.$('.win')
  await el.screenshot({ path: join(outDir, `${name}.png`) })
  console.log(join(outDir, `${name}.png`))
}
await browser.close()
