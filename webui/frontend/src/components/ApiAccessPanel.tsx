import { useState } from 'react'

export interface ApiAccessPanelProps {
  /** OpenAI-compatible base URL, e.g. `http://localhost:8000/v1`. */
  baseUrl: string
  /** Bearer token, or null when the server runs with auth disabled. */
  token: string | null
  /** Available model ids (blueprints) from `/v1/models`. */
  models: string[]
}

export interface Snippets {
  curl: string
  python: string
  openWebUI: string
}

/** Ready-to-paste client snippets, pre-filled with the live base URL + model. */
export function buildSnippets(baseUrl: string, token: string | null, model: string): Snippets {
  const key = token && token.length > 0 ? token : 'not-needed'
  return {
    curl: [
      `curl -sf ${baseUrl}/chat/completions \\`,
      `  -H "Authorization: Bearer ${key}" \\`,
      `  -H "Content-Type: application/json" \\`,
      `  -d '{"model":"${model}","messages":[{"role":"user","content":"ping"}]}'`,
    ].join('\n'),
    python: [
      'from openai import OpenAI',
      `client = OpenAI(base_url="${baseUrl}", api_key="${key}")`,
      'resp = client.chat.completions.create(',
      `    model="${model}",`,
      '    messages=[{"role": "user", "content": "ping"}],',
      ')',
      'print(resp.choices[0].message.content)',
    ].join('\n'),
    openWebUI: [
      'Open WebUI → Settings → Connections → OpenAI API',
      `  Base URL: ${baseUrl}`,
      `  API Key:  ${key}`,
    ].join('\n'),
  }
}

function CopyBlock({ label, code }: { label: string; code: string }) {
  const [copied, setCopied] = useState(false)
  const onCopy = async () => {
    try {
      await navigator.clipboard?.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable (insecure context) — silently ignore */
    }
  }
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-base-content/70">{label}</span>
        <button type="button" className="btn btn-xs" onClick={onCopy} aria-label={`Copy ${label} snippet`}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="bg-base-300 rounded p-3 text-xs overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  )
}

/**
 * "Connect any OpenAI client" — surfaces the live base URL, token, model list,
 * and copy-paste snippets so the server can be plugged into Open WebUI, Cursor,
 * the OpenAI SDK, or curl with no guesswork.
 */
export function ApiAccessPanel({ baseUrl, token, models }: ApiAccessPanelProps) {
  const fallback = models[0] ?? 'cli_fusion'
  const [selected, setSelected] = useState(fallback)
  const model = models.includes(selected) ? selected : fallback
  const snippets = buildSnippets(baseUrl, token, model)

  return (
    <div>
      <p className="text-sm text-base-content/70">
        Point any OpenAI-compatible client at this server. The <code>model</code> field selects the
        blueprint (e.g. <code>cli_fusion</code>).{' '}
        {token ? 'Use your API token as the key.' : 'Auth is disabled — any key works.'}
      </p>

      <div className="grid gap-2 sm:grid-cols-2 mt-3 text-sm">
        <div>
          <span className="font-semibold">Base URL:</span> <code>{baseUrl}</code>
        </div>
        <div>
          <span className="font-semibold">API key:</span>{' '}
          <code>{token ? `…${token.slice(-4)}` : 'any (auth disabled)'}</code>
        </div>
      </div>

      {models.length > 0 && (
        <label className="form-control mt-3 max-w-xs">
          <span className="label-text text-xs">Model</span>
          <select
            className="select select-sm select-bordered"
            value={model}
            aria-label="Model"
            onChange={(e) => setSelected(e.target.value)}
          >
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      )}

      <CopyBlock label="curl" code={snippets.curl} />
      <CopyBlock label="OpenAI Python SDK" code={snippets.python} />
      <CopyBlock label="Open WebUI" code={snippets.openWebUI} />
    </div>
  )
}
