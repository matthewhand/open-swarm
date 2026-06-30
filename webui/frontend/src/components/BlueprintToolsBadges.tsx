import { useQuery } from '@tanstack/react-query'
import { Plug, ShieldCheck } from 'lucide-react'
import { fetchBlueprintTools } from '../lib/api'

/** Shows a blueprint's capability tool needs resolved to MCP providers, when it
 *  declares `tool_requirements`. Renders nothing otherwise. */
export function BlueprintToolsBadges({ blueprintId }: { blueprintId: string | undefined }) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['bp-tools', blueprintId],
    queryFn: () => fetchBlueprintTools(blueprintId!),
    enabled: !!blueprintId,
  })

  if (!blueprintId) return null

  if (isPending) {
    return (
      <div className="mt-3 rounded-lg bg-base-200 p-3 flex items-center gap-2 text-sm text-base-content/70" aria-live="polite" aria-busy="true">
        <span className="loading loading-spinner loading-sm" /> Loading tools...
      </div>
    )
  }

  if (isError) {
    return (
      <div className="mt-3 rounded-lg bg-error/10 p-3 text-sm text-error" aria-live="assertive" role="alert">
        Failed to load resolved tools.
      </div>
    )
  }

  const reqs = data?.requirements ?? {}
  if (Object.keys(reqs).length === 0) {
    return (
      <div className="mt-3 rounded-lg bg-base-200 p-3 text-sm text-base-content/50" role="status">
        No tool requirements specified.
      </div>
    )
  }

  return (
    <div className="mt-3 rounded-lg bg-base-200 p-3" role="group" aria-label="Resolved tools">
      <div className="mb-1 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-base-content/70">
        <Plug className="h-3.5 w-3.5" /> Resolved tools (MCP)
      </div>
      <ul className="space-y-0.5 text-sm">
        {Object.entries(reqs).map(([cap, level]) => {
          const server = data?.satisfied?.[cap]
          return (
            <li key={cap} className="flex flex-wrap items-center gap-1.5">
              <code className="text-xs">{cap}</code>
              <span className="text-base-content/50">({level})</span>
              <span aria-hidden>→</span>
              {server ? (
                <span className="badge badge-success badge-sm gap-1">
                  <ShieldCheck className="h-3 w-3" /> {server}
                </span>
              ) : (
                <span className="badge badge-ghost badge-sm">unresolved</span>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
