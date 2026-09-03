import { escapeHtml } from './htmlSafe'

/** CSS class on the <pre> that hosts highlighted Python (REQ-25). */
export const PYTHON_CODE_CLASS = 'os-code-python'

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

const IDENT = /[A-Za-z_][A-Za-z0-9_]*/
const NUMBER = /(?:0[xX][0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/

function span(kind: string, text: string): string {
  return `<span class="os-py-${kind}">${escapeHtml(text)}</span>`
}

/**
 * Highlight Python source as allowlisted HTML spans.
 * Output is safe to assign via dangerouslySetInnerHTML.
 */
export function highlightPython(source: string): string {
  const text = String(source ?? '')
  if (!text) return ''
  let out = ''
  let i = 0
  let prevWord = ''

  const pushPlain = (chunk: string) => {
    out += escapeHtml(chunk)
  }

  while (i < text.length) {
    const ch = text[i]

    if (ch === '#') {
      const end = text.indexOf('\n', i)
      const comment = end === -1 ? text.slice(i) : text.slice(i, end)
      out += span('cmt', comment)
      i += comment.length
      prevWord = ''
      continue
    }

    if (ch === "'" || ch === '"') {
      const triple = text.startsWith(ch + ch + ch, i)
      const quote = triple ? ch + ch + ch : ch
      let j = i + quote.length
      if (triple) {
        const close = text.indexOf(quote, j)
        const body = close === -1 ? text.slice(i) : text.slice(i, close + 3)
        out += span('str', body)
        i += body.length
      } else {
        while (j < text.length) {
          if (text[j] === '\\' && j + 1 < text.length) {
            j += 2
            continue
          }
          if (text[j] === ch) {
            j += 1
            break
          }
          if (text[j] === '\n') break
          j += 1
        }
        out += span('str', text.slice(i, j))
        i = j
      }
      prevWord = ''
      continue
    }

    const ident = text.slice(i).match(IDENT)
    if (ident && ident.index === 0) {
      const word = ident[0]
      if (KEYWORDS.has(word)) {
        out += span('kw', word)
      } else if (prevWord === 'def' || prevWord === 'class') {
        out += span('fn', word)
      } else {
        pushPlain(word)
      }
      prevWord = word
      i += word.length
      continue
    }

    const num = text.slice(i).match(NUMBER)
    if (num && num.index === 0) {
      out += span('num', num[0])
      i += num[0].length
      prevWord = ''
      continue
    }

    pushPlain(ch)
    if (/\s/.test(ch)) {
      /* keep prevWord across whitespace so `def name` still highlights */
    } else {
      prevWord = ''
    }
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
