import { useId, useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Gauge } from 'lucide-react'
import { formatUsageTokens, type ContextUsage } from '../lib/contextUsage'
import './apiComposerUsage.css'

export function ApiComposerUsage({ usage, onOpenDetail }: {
  usage: ContextUsage | null
  onOpenDetail?: () => void
}) {
  const [open, setOpen] = useState(false)
  const id = useId()
  const toggle = useRef<HTMLButtonElement>(null)
  const used = Math.max(0, usage?.tokens ?? 0)
  const limit = usage?.window && usage.window > 0 ? usage.window : null
  const percent = limit ? Math.round(used / limit * 1000) / 10 : null
  const level = percent != null && percent >= 95 ? 'high' : percent != null && percent >= 80 ? 'medium' : 'low'
  const number = (value: number) => formatUsageTokens(value)
  const Chevron = open ? ChevronDown : ChevronUp

  return (
    <div className="os-api-usage" data-level={level} onKeyDown={event => {
      if (event.key === 'Escape' && open) {
        event.stopPropagation()
        setOpen(false)
        toggle.current?.focus()
      }
    }}>
      {open ? (
        <section id={id} className="os-api-usage__details" aria-label="Token usage details">
          <div className="os-api-usage__heading">
            <strong>Conversation usage</strong>
            {usage ? <span className="os-api-usage__source">{usage.estimate ? 'Estimated' : 'Reported'}</span> : null}
          </div>
          {usage ? <>
            <div className="os-api-usage__stats">
              <div><span>Context used</span><strong>{number(used)} <small>tokens</small></strong></div>
              <div><span>Last reply</span><strong>{usage.last_output > 0 ? <>{number(usage.last_output)} <small>tokens</small></> : <small>Not available yet</small>}</strong></div>
            </div>
            {limit && percent != null ? (
              <div className="os-api-usage__capacity">
                <div><span>{percent}% of context used</span><span>{number(limit)} token limit</span></div>
                <div className="os-api-usage__track" role="progressbar" aria-label="Context capacity used"
                  aria-valuemin={0} aria-valuemax={limit} aria-valuenow={Math.min(used, limit)}
                  aria-valuetext={`${number(used)} of ${number(limit)} tokens; ${percent}% used`}>
                  <span style={{ width: `${Math.min(100, percent)}%` }} />
                </div>
              </div>
            ) : <p className="os-api-usage__note">Context capacity is not reported by this model.</p>}
            <dl className="os-api-usage__breakdown">
              {(['Messages', 'Summaries', 'Instructions', 'Tools'] as const).map((label, index) => {
                const key = (['messages', 'summaries', 'system', 'tools'] as const)[index]
                return <div key={key}><dt>{label}</dt><dd>{number(usage.breakdown?.[key] ?? 0)}</dd></div>
              })}
            </dl>
            <div className="os-api-usage__footnote">
              <p>Tokens are chunks of text the model processes.{usage.estimate ? ' These counts are estimated from text length.' : ''}</p>
              {onOpenDetail ? <button type="button" onClick={onOpenDetail}>More details</button> : null}
            </div>
          </> : <p className="os-api-usage__note">Usage will appear here after your conversation is measured.</p>}
        </section>
      ) : null}
      <button ref={toggle} type="button" className="os-api-usage__toggle"
        data-testid={usage ? 'context-usage-badge' : 'composer-usage-toggle'}
        aria-label="Context window usage" aria-expanded={open} aria-controls={open ? id : undefined}
        onClick={() => setOpen(value => !value)}>
        <Gauge size={14} aria-hidden="true" />
        <span>{usage ? 'Context' : 'Token usage'}</span>
        <strong>{usage ? `${number(used)} tokens` : 'Not yet measured'}</strong>
        <Chevron size={14} aria-hidden="true" />
      </button>
    </div>
  )
}
