import { useEffect, useRef } from 'react'
import type { RemoteConnection } from '../lib/api'
import { remoteDisplayName } from '../lib/remotesCatalog'

export interface RemoteSessionsPopupProps {
  isOpen: boolean
  onClose: () => void
  remotes: RemoteConnection[]
  onOpenSettingsRemotes: () => void
}

/** Strip sensitive authentication query params from remote URLs (REQ-118). */
export function cleanRemoteUrl(rawUrl: string): string {
  try {
    const parsed = new URL(rawUrl)
    const sensitive = ['token', 'api_key', 'apikey', 'key', 'auth', 'auth_token', 'password', 'secret']
    for (const param of Array.from(parsed.searchParams.keys())) {
      if (sensitive.some((s) => param.toLowerCase().includes(s))) {
        parsed.searchParams.delete(param)
      }
    }
    return parsed.toString()
  } catch {
    return rawUrl
  }
}

export function isBrowsableRemote(remote: RemoteConnection): boolean {
  const target = (remote.ui_url?.trim() || remote.base_url?.trim()) ?? ''
  return Boolean(target && /^https?:\/\//i.test(target))
}

export default function RemoteSessionsPopup({
  isOpen,
  onClose,
  remotes,
  onOpenSettingsRemotes,
}: RemoteSessionsPopupProps) {
  const popupRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        onClose()
      }
    }
    const handlePointerDown = (event: PointerEvent) => {
      if (popupRef.current && !popupRef.current.contains(event.target as Node)) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('pointerdown', handlePointerDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  const browsable = remotes.filter(isBrowsableRemote)

  return (
    <div
      ref={popupRef}
      role="menu"
      aria-label="Remote sessions"
      className="absolute bottom-full left-0 mb-2 w-64 rounded-box border border-base-300 bg-base-100 shadow-xl z-50 overflow-hidden"
      data-testid="remote-sessions-popup"
    >
      <div className="p-2">
        <div className="px-2 py-1 font-semibold text-base-content/80 text-[11px] uppercase tracking-wider">
          Remote sessions
        </div>
        {browsable.length === 0 ? (
          <div className="px-2 py-2 text-xs text-base-content/65" data-testid="remotes-empty-state">
            <p>No remotes configured</p>
            <button
              type="button"
              className="mt-1 text-primary hover:underline block text-left"
              onClick={() => {
                onClose()
                onOpenSettingsRemotes()
              }}
            >
              Configure in Settings
            </button>
          </div>
        ) : (
          <ul className="menu menu-xs p-0 gap-0.5" role="none">
            {browsable.map((remote) => {
              const raw = remote.ui_url?.trim() || remote.base_url?.trim() || ''
              const url = cleanRemoteUrl(raw)
              const label = remoteDisplayName(remote)
              return (
                <li key={remote.id} role="none">
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    role="menuitem"
                    className="flex flex-col items-start gap-0.5 py-1.5 px-2 rounded hover:bg-base-200"
                    onClick={onClose}
                  >
                    <span className="font-medium text-base-content">{label}</span>
                    <span className="text-[11px] text-base-content/60 truncate max-w-[14rem]">
                      {url}
                    </span>
                  </a>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
