import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Book, PlusCircle, Settings, Users } from 'lucide-react'
import { Badge, Card } from '../components/DaisyUI'

const QUICK_ACTIONS = [
  {
    href: '/teams/launch/',
    title: 'Launch Team',
    description: 'Stand up a blueprint team and expose it as an API model.',
    icon: PlusCircle,
  },
  {
    href: '/blueprint-library/',
    title: 'Browse Blueprints',
    description: 'Open the library of multi-agent blueprints you can run.',
    icon: Book,
  },
  {
    href: '/teams/',
    title: 'Manage Teams',
    description: 'Inspect the registry, aliases, and launched team admin.',
    icon: Users,
  },
  {
    href: '/settings/',
    title: 'Settings',
    description: 'Profiles, credentials, and operator configuration.',
    icon: Settings,
  },
] as const

export default function Dashboard() {
  const statsQuery = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const [bpRes, mRes, tRes, healthRes] = await Promise.all([
        fetch('/v1/blueprints'),
        fetch('/v1/models'),
        fetch('/v1/teams/').catch(() => fetch('/teams/export?format=json')),
        fetch('/health').catch(() => null),
      ])
      const bpJson = bpRes.ok ? await bpRes.json() : { data: [] }
      const mJson = mRes.ok ? await mRes.json() : { data: [] }
      let tCount = 0
      if (tRes && tRes.ok) {
        const tJson = await tRes.json()
        if (Array.isArray(tJson?.data)) tCount = tJson.data.length
        else if (tJson && typeof tJson === 'object') tCount = Object.keys(tJson).length
      }
      return {
        blueprintCount: Array.isArray(bpJson?.data) ? bpJson.data.length : 0,
        modelCount: Array.isArray(mJson?.data) ? mJson.data.length : 0,
        teamsCount: tCount,
        apiOnline: healthRes ? healthRes.ok : bpRes.ok || mRes.ok,
      }
    },
    refetchInterval: 30_000,
    retry: 1,
  })

  const loadingStats = statsQuery.isPending
  const errorStats = statsQuery.isError
    ? 'Could not load live stats. Is the API running?'
    : null
  const teamsCount = statsQuery.data?.teamsCount ?? null
  const blueprintCount = statsQuery.data?.blueprintCount ?? null
  const modelCount = statsQuery.data?.modelCount ?? null
  const apiOnline = statsQuery.data ? statsQuery.data.apiOnline : null

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="sr-only">Home</h1>

      <section aria-labelledby="quick-actions-heading">
        <h2 id="quick-actions-heading" className="sr-only">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <a key={action.href} href={action.href} className="os-action-card">
                <span className="os-action-card__icon" aria-hidden="true">
                  <Icon className="h-6 w-6" />
                </span>
                <span>
                  <span className="os-action-card__title">{action.title}</span>
                  <p className="os-action-card__desc">{action.description}</p>
                </span>
              </a>
            )
          })}
        </div>
      </section>

      {errorStats && (
        <p className="text-sm text-base-content/55" role="status">
          {errorStats}
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatTile
          label="Teams"
          value={loadingStats ? '…' : String(teamsCount ?? 0)}
          hint="LLM-profile aliases"
        />
        <StatTile
          label="Blueprints"
          value={loadingStats ? '…' : String(blueprintCount ?? 0)}
          hint="Discoverable blueprints"
        />
        <StatTile
          label="Models"
          value={loadingStats ? '…' : String(modelCount ?? 0)}
          hint="Exposed as OpenAI models"
        />
      </div>

      <Card title="Getting started" bordered>
        {(teamsCount === 0 || teamsCount === null) && !loadingStats ? (
          <div className="space-y-3 text-sm text-base-content/75">
            <p>No teams registered yet. Launch a blueprint team to expose a custom model id on the API.</p>
            <a href="/teams/launch/" className="btn btn-primary btn-sm">
              Launch your first team
            </a>
          </div>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-sm text-base-content/70">
            <li>
              Point OpenAI clients at <code className="text-xs">/v1</code> with your API token.
            </li>
            <li>
              Browse blueprints at <code className="text-xs">/blueprint-library/</code>, then launch via
              Teams or <code className="text-xs">swarm-cli</code>.
            </li>
            <li>
              Sessions, creators, and full settings live on the Django shell (
              <code className="text-xs">ENABLE_WEBUI=true</code>).
            </li>
            <li>
              SPA chat is at <Link className="link" to="/chat">/chat</Link> (Django session cookie).
            </li>
          </ul>
        )}
      </Card>

      <Card title="API status" bordered>
        <div className="flex items-center justify-between rounded-lg bg-base-200 p-3">
          <div className="flex items-center gap-3">
            <div
              className={`h-2.5 w-2.5 rounded-full ${
                apiOnline === null ? 'bg-base-300' : apiOnline ? 'bg-success' : 'bg-error'
              }`}
            />
            <span>OpenAI-compatible API</span>
          </div>
          <Badge type={apiOnline ? 'success' : apiOnline === false ? 'error' : 'ghost'}>
            {apiOnline === null ? 'Checking…' : apiOnline ? 'Reachable' : 'Unreachable'}
          </Badge>
        </div>
      </Card>
    </div>
  )
}

function StatTile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-base-300 bg-base-200/70 px-4 py-3">
      <div className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-base-content/45">
        {label}
      </div>
      <div className="mt-1 text-3xl font-semibold tabular-nums tracking-tight text-base-content">
        {value}
      </div>
      <div className="mt-1 text-xs text-base-content/45">{hint}</div>
    </div>
  )
}
