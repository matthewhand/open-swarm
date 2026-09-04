import type { AgentStatus } from '../../types/agent'

export function AgentStatusBadge({
  status,
  showText = true,
}: {
  status: AgentStatus
  showText?: boolean
}) {
  const color =
    status === 'working'
      ? 'badge-info'
      : status === 'error'
        ? 'badge-error'
        : status === 'waiting'
          ? 'badge-warning'
          : 'badge-ghost'
  return (
    <span className={`badge badge-xs ${color}`} title={status}>
      {showText ? status : <span className="w-1.5 h-1.5 rounded-full bg-current" />}
    </span>
  )
}
