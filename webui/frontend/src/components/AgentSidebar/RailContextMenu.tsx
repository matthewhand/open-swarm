import type { ReactNode, Ref } from 'react'

/**
 * Shared rail right-click menu chrome (REQ-104 / #435).
 *
 * #435 may add Unpin / unread / Edit / Duplicate / Copy id / Hide / Delete
 * as additional items — keep this list composable so those PRs merge cleanly.
 */
export interface RailMenuItem {
  id: string
  label: string
  icon: ReactNode
  onSelect: () => void
  hidden?: boolean
  danger?: boolean
  testId?: string
}

export interface RailContextMenuProps {
  agentName: string
  x: number
  y: number
  items: readonly RailMenuItem[]
  menuRef?: Ref<HTMLDivElement>
}

export function RailContextMenu({ agentName, x, y, items, menuRef }: RailContextMenuProps) {
  const visible = items.filter((item) => !item.hidden)
  return (
    <div
      ref={menuRef}
      role="menu"
      aria-label={`Actions for ${agentName}`}
      className="fixed z-50 min-w-[12.5rem] rounded-lg border border-base-300 bg-neutral py-1 text-sm shadow-xl"
      style={{ left: x, top: y }}
      data-testid="rail-context-menu"
    >
      {visible.map((item) => (
        <button
          key={item.id}
          type="button"
          role="menuitem"
          data-testid={item.testId || `rail-menu-${item.id}`}
          className={
            item.danger
              ? 'flex w-full items-center gap-2 px-3 py-2 text-left text-error hover:bg-base-300/50'
              : 'flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50'
          }
          onClick={item.onSelect}
        >
          {item.icon}
          {item.label}
        </button>
      ))}
    </div>
  )
}
