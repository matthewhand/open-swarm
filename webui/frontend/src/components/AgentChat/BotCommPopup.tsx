import type { DelegationEvent } from '../../types/agent'

export function BotCommPopup({
  delegation,
  onClose,
}: {
  delegation: DelegationEvent
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="presentation">
      <div role="dialog" aria-modal="true" className="w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-4 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-sm">Bot-to-Bot Delegation</h2>
          <button type="button" className="btn btn-ghost btn-xs" onClick={onClose} aria-label="Close dialog">
            Close
          </button>
        </div>
        <p className="text-xs text-base-content/60 mb-2">
          {delegation.from_agent_name} → {delegation.to_agent_name}
        </p>
        <p className="text-sm mb-2">{delegation.query}</p>
        {delegation.response && (
          <p className="text-sm bg-base-200 rounded-lg p-2">{delegation.response}</p>
        )}
      </div>
    </div>
  )
}
