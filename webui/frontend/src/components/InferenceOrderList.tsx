import { useRef, useState } from 'react'
import { GripVertical, Plus, X } from 'lucide-react'
import type { InferenceKind, InferenceSeat } from '../lib/inferenceList'
import { seatKey } from '../lib/inferenceList'

export interface InferenceCatalogOption {
  id: string
  kind: InferenceKind
  label: string
}

interface InferenceOrderListProps {
  seats: InferenceSeat[]
  catalog: InferenceCatalogOption[]
  defaultLabel: string
  onChange: (next: InferenceSeat[]) => void
}

/**
 * Prominent ordered inference list (REQ-69). Native HTML5 drag to reorder.
 * Not a single <select> of the live order.
 */
export default function InferenceOrderList({
  seats,
  catalog,
  defaultLabel,
  onChange,
}: InferenceOrderListProps) {
  const [addValue, setAddValue] = useState('')
  const dragFrom = useRef<number | null>(null)

  const unused = catalog.filter(
    (opt) => !seats.some((seat) => seat.kind === opt.kind && seat.id === opt.id),
  )

  const move = (from: number, to: number) => {
    if (from === to || from < 0 || to < 0 || from >= seats.length || to >= seats.length) return
    const next = seats.slice()
    const [row] = next.splice(from, 1)
    next.splice(to, 0, row)
    onChange(next)
  }

  const add = () => {
    if (!addValue) return
    const opt = unused.find((item) => seatKey(item) === addValue)
    if (!opt) return
    onChange([...seats, { id: opt.id, kind: opt.kind, label: opt.label }])
    setAddValue('')
  }

  return (
    <div
      className="space-y-3 rounded-box border border-base-300 bg-base-200/40 p-3"
      data-testid="inference-order-list"
    >
      <div>
        <span className="text-sm font-semibold text-base-content/80">Ordered inference</span>
        <p className="text-xs text-base-content/60 mt-0.5">
          First is preference 1. Scale-out spreads work down this list. Config
          failures try the next. Empty uses Settings default ({defaultLabel}).
        </p>
      </div>

      {seats.length === 0 ? (
        <p className="text-sm text-base-content/60" data-testid="inference-list-empty">
          Empty list — using {defaultLabel}.
        </p>
      ) : (
        <ol className="space-y-1" data-testid="inference-list-items">
          {seats.map((seat, index) => (
            <li
              key={seatKey(seat)}
              draggable
              data-testid="inference-list-row"
              data-seat={seatKey(seat)}
              data-index={index}
              className="flex items-center gap-2 rounded-box border border-base-300 bg-base-100 px-2 py-1.5 cursor-grab active:cursor-grabbing"
              onDragStart={(event) => {
                dragFrom.current = index
                event.dataTransfer.effectAllowed = 'move'
                event.dataTransfer.setData('text/plain', String(index))
              }}
              onDragOver={(event) => {
                event.preventDefault()
                event.dataTransfer.dropEffect = 'move'
              }}
              onDrop={(event) => {
                event.preventDefault()
                const from = dragFrom.current
                dragFrom.current = null
                if (from === null) return
                move(from, index)
              }}
            >
              <GripVertical className="h-4 w-4 shrink-0 text-base-content/40" aria-hidden="true" />
              <span className="badge badge-ghost badge-sm font-mono">{index + 1}</span>
              <span className="flex-1 truncate text-sm">
                {seat.label || seat.id}
                <span className="ml-1 text-xs text-base-content/50">{seat.kind}</span>
              </span>
              <button
                type="button"
                className="btn btn-ghost btn-xs btn-square"
                aria-label={`Remove ${seat.id}`}
                onClick={() => onChange(seats.filter((_, i) => i !== index))}
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ol>
      )}

      <div className="flex gap-2">
        <select
          className="select select-bordered select-sm flex-1"
          aria-label="Add inference option"
          data-testid="inference-list-add"
          value={addValue}
          onChange={(event) => setAddValue(event.target.value)}
        >
          <option value="">Add from catalog…</option>
          {unused.map((opt) => (
            <option key={seatKey(opt)} value={seatKey(opt)}>
              {opt.label} ({opt.kind})
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-sm btn-outline"
          disabled={!addValue}
          aria-label="Add inference seat"
          onClick={add}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
