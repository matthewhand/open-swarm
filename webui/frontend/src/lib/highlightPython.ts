/**
 * Small Python highlighter for chat fenced code blocks.
 * Avoids a highlight.js dependency; tokens become allowlisted <span class="...">.
 */

const KEYWORDS = new Set([
  'False',
  'None',
  'True',
  'and',
  'as',
  'assert',
  'async',
  'await',
  'break',
  'class',
  'continue',
  'def',
  'del',
  'elif',
  'else',
  'except',
  'finally',
  'for',
  'from',
  'global',
  'if',
  'import',
  'in',
  'is',
  'lambda',
  'nonlocal',
  'not',
  'or',
  'pass',
  'raise',
  'return',
  'try',
  'while',
  'with',
  'yield',
])

const BUILTINS = new Set([
  'Exception',
  'abs',
  'bool',
  'dict',
  'enumerate',
  'float',
  'int',
  'len',
  'list',
  'print',
  'range',
  'set',
  'str',
  'super',
  'type',
])

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function span(kind: string, raw: string): string {
  return `<span class="os-py-${kind}">${escapeHtml(raw)}</span>`
}

/** Highlight a Python source string as HTML (already escaped inside tokens). */
export function highlightPython(source: string): string {
  const text = String(source ?? '')
  if (!text) return ''
  let i = 0
  let out = ''
  const n = text.length

  const takeWhile = (pred: (ch: string) => boolean): string => {
    const start = i
    while (i < n && pred(text[i])) i += 1
    return text.slice(start, i)
  }

  while (i < n) {
    const ch = text[i]
    const next = i + 1 < n ? text[i + 1] : ''

    if (ch === '#') {
      out += span('com', takeWhile((c) => c !== '\n'))
      continue
    }

    if ((ch === '"' || ch === "'") && text.slice(i, i + 3) === ch + ch + ch) {
      const quote = ch + ch + ch
      i += 3
      let body = quote
      while (i < n && text.slice(i, i + 3) !== quote) {
        if (text[i] === '\\' && i + 1 < n) {
          body += text[i] + text[i + 1]
          i += 2
        } else {
          body += text[i]
          i += 1
        }
      }
      if (i < n) {
        body += quote
        i += 3
      }
      out += span('str', body)
      continue
    }

    if (ch === '"' || ch === "'") {
      const quote = ch
      i += 1
      let body = quote
      while (i < n && text[i] !== quote) {
        if (text[i] === '\\' && i + 1 < n) {
          body += text[i] + text[i + 1]
          i += 2
        } else {
          if (text[i] === '\n') break
          body += text[i]
          i += 1
        }
      }
      if (i < n && text[i] === quote) {
        body += quote
        i += 1
      }
      out += span('str', body)
      continue
    }

    if (ch === '@') {
      i += 1
      const name = takeWhile((c) => /[A-Za-z0-9_]/.test(c))
      out += span('dec', `@${name}`)
      continue
    }

    if (/[0-9]/.test(ch) || (ch === '.' && /[0-9]/.test(next))) {
      out += span('num', takeWhile((c) => /[0-9.eE_+-]/.test(c)))
      continue
    }

    if (/[A-Za-z_]/.test(ch)) {
      const ident = takeWhile((c) => /[A-Za-z0-9_]/.test(c))
      if (KEYWORDS.has(ident)) out += span('kw', ident)
      else if (BUILTINS.has(ident)) out += span('bi', ident)
      else out += escapeHtml(ident)
      continue
    }

    out += escapeHtml(ch)
    i += 1
  }
  return out
}

export function isPythonFence(lang: string | undefined | null): boolean {
  const normalized = String(lang || '')
    .trim()
    .toLowerCase()
    .split(/[\s{]/)[0]
  return normalized === 'python' || normalized === 'py'
}
