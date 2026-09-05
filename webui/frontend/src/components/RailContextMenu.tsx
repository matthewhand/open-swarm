import { Fragment, type Ref } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  Circle,
  ClipboardCopy,
  CopyPlus,
  Eye,
  EyeOff,
  Pencil,
  Pin,
  PinOff,
  Trash2,
  Users,
} from 'lucide-react'
import type { RailMenuItemId, RailMenuItemSpec } from '../lib/railContextMenu'

const ICONS: Record<RailMenuItemId, LucideIcon> = {
  'select-agent': Users,
  unpin: PinOff,
  pin: Pin,
  unread: Circle,
  edit: Pencil,
  duplicate: CopyPlus,
  'copy-id': ClipboardCopy,
  hide: EyeOff,
  unhide: Eye,
  delete: Trash2,
}

export interface RailMenuItemProps {
  spec: RailMenuItemSpec
  onSelect: (id: RailMenuItemId) => void
}

/** Shared icon+label row for rail / section / compacted-card menus (REQ-82). */
export function RailMenuItem({ spec, onSelect }: RailMenuItemProps) {
  const Icon = ICONS[spec.id]
  const danger = Boolean(spec.danger)
  return (
    <li className={spec.disabled ? 'disabled' : undefined}>
      <button
        type="button"
        role="menuitem"
        disabled={spec.disabled}
        title={spec.reason}
        data-menu-id={spec.id}
        className={danger ? 'text-error' : undefined}
        onClick={() => {
          if (spec.disabled) return
          onSelect(spec.id)
        }}
      >
        <Icon
          className={`h-4 w-4 ${danger ? 'text-error' : ''}`}
          aria-hidden="true"
          data-menu-icon={spec.id}
        />
        {spec.label}
      </button>
    </li>
  )
}

export interface RailContextMenuProps {
  agentName: string
  x: number
  y: number
  items: RailMenuItemSpec[]
  menuRef?: Ref<HTMLUListElement>
  onSelect: (id: RailMenuItemId) => void
}

export default function RailContextMenu({
  agentName,
  x,
  y,
  items,
  menuRef,
  onSelect,
}: RailContextMenuProps) {
  const groups: RailMenuItemSpec[][] = []
  for (const item of items) {
    const last = groups[groups.length - 1]
    if (!last || last[0].group !== item.group) {
      groups.push([item])
    } else {
      last.push(item)
    }
  }

  return (
    <ul
      ref={menuRef}
      role="menu"
      aria-label={`Actions for ${agentName}`}
      className="menu menu-sm rounded-box fixed z-50 min-w-52 border border-base-300 bg-base-100 p-1 shadow-xl"
      style={{ left: x, top: y }}
      data-testid="rail-context-menu"
    >
      {groups.map((group, index) => (
        <Fragment key={group[0].id}>
          {index > 0 ? (
            <li aria-hidden="true" className="pointer-events-none px-2 py-0.5">
              <hr className="border-base-300" />
            </li>
          ) : null}
          {group.map((spec) => (
            <RailMenuItem key={spec.id} spec={spec} onSelect={onSelect} />
          ))}
        </Fragment>
      ))}
    </ul>
  )
}
