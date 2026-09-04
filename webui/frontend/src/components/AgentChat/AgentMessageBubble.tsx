import { useState } from 'react'
import { Check, Copy, FoldVertical, RotateCcw, ScrollText } from 'lucide-react'
import type { Agent, ChatMessage } from '../../types/agent'
import { AgentAvatar } from '../AgentSidebar/AgentAvatar'
import { roleMeta } from '../../lib/agent-roles'
import { renderSafeMarkdown } from '../../lib/markdown'

interface AgentMessageBubbleProps {
  message: ChatMessage
  agent?: Agent
  onOpenDelegation?: (delegationId: string) => void
  canCompact?: boolean
  compacting?: boolean
  regenerating?: boolean
  onCompactToHere?: () => void
  onRegenerateSummary?: (steer: string) => void
  onResolveApproval?: (status: 'approved' | 'rejected') => void
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function AgentMessageBubble({
  message,
  agent,
  onOpenDelegation,
  canCompact = false,
  compacting = false,
  regenerating = false,
  onCompactToHere,
  onRegenerateSummary,
  onResolveApproval,
}: AgentMessageBubbleProps) {
  const isUser = message.role === 'user'
  const isSummary = message.kind === 'summary'
  const [copied, setCopied] = useState(false)
  const [originalOpen, setOriginalOpen] = useState(false)
  const [steer, setSteer] = useState('')

  const handleCopy = async () => {
    const ok = await copyText(message.text)
    if (!ok) return
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  if (message.kind === 'approval') {
    const pending = (message.approval?.status || 'pending') === 'pending'
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] w-full rounded-none border border-warning/50 bg-warning/10 px-3.5 py-2.5 text-sm">
          <div className="text-[11px] font-bold uppercase tracking-wider text-warning mb-1">
            Stupidity checker · needs approval
          </div>
          <p className="whitespace-pre-wrap">{message.text}</p>
          {pending ? (
            <div className="mt-2 flex gap-1">
              <button
                type="button"
                className="btn btn-xs btn-warning rounded-none"
                onClick={() => onResolveApproval?.('approved')}
              >
                Approve
              </button>
              <button
                type="button"
                className="btn btn-xs btn-ghost rounded-none"
                onClick={() => onResolveApproval?.('rejected')}
              >
                Reject
              </button>
            </div>
          ) : (
            <p className="mt-1 text-[11px] uppercase tracking-wide opacity-70">
              {message.approval?.status}
            </p>
          )}
        </div>
      </div>
    )
  }

  if (message.kind === 'review' && message.oversightRole) {
    const meta = roleMeta(message.oversightRole)
    return (
      <div className={`flex gap-2 group ${isUser ? 'justify-end' : 'justify-start'}`}>
        {!isUser && agent && <AgentAvatar agent={agent} size={32} />}
        <div className="relative max-w-[80%]">
          <div className="rounded-sm border-l-4 border-primary bg-base-200 px-3.5 py-2 text-sm whitespace-pre-wrap">
            <div className="text-[11px] font-bold uppercase tracking-wider text-primary/80 mb-0.5">
              {meta.label}
              {message.agent ? ` · ${message.agent}` : ''}
            </div>
            {message.text}
          </div>
          <div className="absolute -top-3 right-1 flex items-center gap-0.5 rounded-full border border-base-300 bg-base-100 px-0.5 py-0.5 shadow-sm opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-opacity">
            <button
              type="button"
              className="btn btn-ghost btn-xs btn-circle"
              aria-label={copied ? 'Copied' : 'Copy message'}
              title="Copy to clipboard"
              onClick={handleCopy}
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (isSummary) {
    return (
      <div className="flex justify-start group">
        <div className="relative max-w-[85%] w-full rounded-none border border-base-content/25 bg-base-300/50 px-3.5 py-2.5 text-sm shadow-xs">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-base-content/55">
              Conversation summary
            </span>
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-square"
                aria-label={copied ? 'Copied' : 'Copy summary'}
                title="Copy summary"
                onClick={handleCopy}
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-square"
                aria-label="Regenerate summary"
                title="Regenerate summary"
                disabled={regenerating || !onRegenerateSummary}
                onClick={() => onRegenerateSummary?.(steer)}
              >
                <RotateCcw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-square"
                aria-label="View original messages"
                title="View original messages"
                onClick={() => setOriginalOpen(true)}
              >
                <ScrollText className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <p className="whitespace-pre-wrap">{regenerating ? 'Regenerating summary…' : message.text}</p>
          <label className="mt-2 block">
            <span className="sr-only">Steer next regenerate</span>
            <input
              className="input input-xs input-bordered w-full rounded-none"
              value={steer}
              onChange={(e) => setSteer(e.target.value)}
              placeholder="Steer next regenerate (optional)"
            />
          </label>
        </div>
        {originalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="presentation">
            <div
              role="dialog"
              aria-modal="true"
              aria-label="Original messages"
              className="w-full max-w-lg max-h-[80vh] overflow-y-auto rounded-none border border-base-300 bg-base-100 p-4 shadow-xl"
            >
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-bold text-sm">Original messages</h2>
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  onClick={() => setOriginalOpen(false)}
                  aria-label="Close dialog"
                >
                  Close
                </button>
              </div>
              <ol className="space-y-2 text-sm">
                {(message.compacted || []).map((line, i) => (
                  <li key={`${line.role}-${i}`} className="border border-base-300 rounded-none p-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wide opacity-60 mb-0.5">
                      {line.agent || line.role}
                    </div>
                    <div className="whitespace-pre-wrap">{line.text}</div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`flex gap-2 group ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && agent && <AgentAvatar agent={agent} size={32} />}
      <div className="relative max-w-[80%]">
        <div
          className={`rounded-2xl px-3.5 py-2 text-sm ${
            isUser ? 'bg-primary text-primary-content whitespace-pre-wrap' : 'bg-base-200'
          }`}
        >
          {!isUser && message.agent && (
            <div className="text-[11px] font-semibold opacity-70 mb-0.5">{message.agent}</div>
          )}
          {isUser ? (
            message.text
          ) : (
            <div
              className="os-chat-md break-words [&_p]:my-1 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:underline"
              dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(message.text) }}
            />
          )}
          {message.delegationId && onOpenDelegation && (
            <button
              type="button"
              className="block mt-1 text-[11px] underline"
              onClick={() => onOpenDelegation(message.delegationId!)}
            >
              View delegation
            </button>
          )}
        </div>
        <div className="absolute -top-3 right-1 flex items-center gap-0.5 rounded-full border border-base-300 bg-base-100 px-0.5 py-0.5 shadow-sm opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto group-focus-within:opacity-100 group-focus-within:pointer-events-auto transition-opacity">
          <button
            type="button"
            className="btn btn-ghost btn-xs btn-circle"
            aria-label={copied ? 'Copied' : 'Copy message'}
            title="Copy to clipboard"
            onClick={handleCopy}
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          {canCompact && onCompactToHere && (
            <button
              type="button"
              className="btn btn-ghost btn-xs btn-circle"
              aria-label="Compact to here"
              title="Compact older messages into a summary (keep last 3)"
              disabled={compacting}
              onClick={onCompactToHere}
            >
              <FoldVertical className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
