import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import { LoadingDots } from './DaisyUI'
import { agentMarkColor, agentMarkIndex } from '../lib/hiddenAgents'
import {
  botCountLabel,
  interBotChatHref,
  uniqueHopsInOrder,
  type InterBotHop,
  type InterBotLine as InterBotLineData,
} from '../lib/interBot'

function HopAvatar({ hop, stacked }: { hop: InterBotHop; stacked: boolean }) {
  const color = agentMarkColor(hop.agentId || hop.name)
  return (
    <span
      className={`os-interbot-avatar inline-block h-4 w-4 shrink-0 rounded-full border border-base-100 ${
        stacked ? 'os-interbot-avatar--stacked -ms-1.5 first:ms-0' : ''
      }`}
      data-mark={String(agentMarkIndex(hop.agentId || hop.name))}
      data-agent={hop.agentId}
      title={hop.name}
      aria-hidden="true"
      style={{ backgroundColor: color }}
    />
  )
}

export interface InterBotLineProps {
  line: InterBotLineData
  /** Optional override; default is /chat?blueprint= via the row Link. */
  onSelectAgent?: (hop: InterBotHop) => void
}

function jumpToHop(hop: InterBotHop, onSelectAgent?: (hop: InterBotHop) => void) {
  onSelectAgent?.(hop)
}

export default function InterBotLine({ line, onSelectAgent }: InterBotLineProps) {
  if (line.kind === 'progress') {
    return (
      <div className="os-interbot-line" data-pending="true" role="status">
        <LoadingDots size="sm" aria-label="Inter-bot communication in progress" />
      </div>
    )
  }

  if (line.kind === 'single') {
    return (
      <div className="os-interbot-line inline-flex items-center gap-1.5 text-xs" data-kind="single">
        <span>Message from</span>
        <Link
          to={interBotChatHref(line.hop.agentId)}
          className="os-interbot-jump inline-flex items-center gap-1.5 rounded-md px-0.5 py-0.5 hover:bg-base-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          data-testid="os-interbot-single-jump"
          aria-label={line.hop.name}
          onClick={() => jumpToHop(line.hop, onSelectAgent)}
        >
          <HopAvatar hop={line.hop} stacked={false} />
          <span className="os-interbot-name">{line.hop.name}</span>
        </Link>
      </div>
    )
  }

  return <MultiHopLine line={line} onSelectAgent={onSelectAgent} />
}

function MultiHopLine({
  line,
  onSelectAgent,
}: {
  line: Extract<InterBotLineData, { kind: 'multi' }>
  onSelectAgent?: (hop: InterBotHop) => void
}) {
  const hops = uniqueHopsInOrder(line.hops)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const itemRefs = useRef<Array<HTMLAnchorElement | null>>([])
  const menuId = useId()
  const countLabel = botCountLabel(line.hops.length)
  const triggerLabel = `Messaged ${countLabel}`

  useEffect(() => {
    if (!open) return
    const onDocMouse = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onDocKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('mousedown', onDocMouse)
    document.addEventListener('keydown', onDocKey)
    return () => {
      document.removeEventListener('mousedown', onDocMouse)
      document.removeEventListener('keydown', onDocKey)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    itemRefs.current[activeIndex]?.focus()
  }, [open, activeIndex])

  const move = (delta: number) => {
    if (hops.length === 0) return
    setActiveIndex((current) => (current + delta + hops.length) % hops.length)
  }

  const openMenu = (index = 0) => {
    setActiveIndex(index)
    setOpen(true)
  }

  const handleTriggerKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      openMenu(0)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      openMenu(Math.max(0, hops.length - 1))
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (open) setOpen(false)
      else openMenu(0)
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      triggerRef.current?.focus()
    }
  }

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      move(1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      move(-1)
    } else if (event.key === 'Home') {
      event.preventDefault()
      setActiveIndex(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      setActiveIndex(Math.max(0, hops.length - 1))
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      triggerRef.current?.focus()
    }
  }

  return (
    <div className="os-interbot-line inline-flex items-center gap-1.5 text-xs" data-kind="multi">
      <span>Messaged</span>
      <div
        ref={rootRef}
        className={`dropdown ${open ? 'dropdown-open' : ''}`}
        data-testid="os-interbot-dropdown"
      >
        <button
          ref={triggerRef}
          type="button"
          className="os-interbot-picker btn btn-ghost btn-xs h-auto min-h-0 gap-1.5 px-1 py-0.5 font-normal"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={menuId}
          aria-label={triggerLabel}
          data-testid="os-interbot-multi-trigger"
          onClick={() => {
            setOpen((value) => !value)
            setActiveIndex(0)
          }}
          onKeyDown={handleTriggerKeyDown}
        >
          <span className="os-interbot-avatars inline-flex items-center" aria-hidden="true">
            {line.hops.map((hop) => (
              <HopAvatar key={hop.id} hop={hop} stacked />
            ))}
          </span>
          <span data-testid="os-interbot-count">{countLabel}</span>
        </button>
        {open ? (
          <ul
            id={menuId}
            role="menu"
            aria-label={triggerLabel}
            tabIndex={-1}
            data-testid="os-interbot-menu"
            className="dropdown-content menu menu-sm bg-base-100 rounded-box z-20 mt-1 min-w-44 p-2 shadow"
            onKeyDown={handleMenuKeyDown}
          >
            {hops.map((hop, index) => (
              <li key={hop.id} role="none">
                <Link
                  ref={(node) => {
                    itemRefs.current[index] = node
                  }}
                  role="menuitem"
                  tabIndex={index === activeIndex ? 0 : -1}
                  to={interBotChatHref(hop.agentId)}
                  aria-label={hop.name}
                  className={`inline-flex items-center gap-2 ${index === activeIndex ? 'active' : ''}`}
                  onClick={() => {
                    jumpToHop(hop, onSelectAgent)
                    setOpen(false)
                  }}
                >
                  <HopAvatar hop={hop} stacked={false} />
                  <span>{hop.name}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  )
}
