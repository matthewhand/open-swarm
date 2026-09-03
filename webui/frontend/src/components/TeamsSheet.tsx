import { useEffect, useState } from 'react'
import { Users, X } from 'lucide-react'
import { Modal } from './DaisyUI'
import {
  loadTeamRosters,
  memberKindLabel,
  OPEN_TEAMS_SHEET_EVENT,
  type TeamRoster,
} from '../lib/teamRosters'

export interface TeamsSheetProps {
  open?: boolean
  onClose?: () => void
}

/**
 * Overlay for Manage Teams (REQ-23). Prefer this over ejecting to /teams/.
 * Drag-drop roster editing may live in a sibling PR — this sheet lists
 * current rosters and points at adding members.
 */
export default function TeamsSheet({ open, onClose }: TeamsSheetProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const [teams, setTeams] = useState<TeamRoster[]>([])

  const isOpen = open ?? internalOpen
  const close = () => {
    setInternalOpen(false)
    onClose?.()
  }

  useEffect(() => {
    const onOpen = () => setInternalOpen(true)
    window.addEventListener(OPEN_TEAMS_SHEET_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_TEAMS_SHEET_EVENT, onOpen)
  }, [])

  useEffect(() => {
    if (!isOpen) return
    let cancelled = false
    loadTeamRosters().then((next) => {
      if (!cancelled) setTeams(next)
    })
    return () => {
      cancelled = true
    }
  }, [isOpen])

  return (
    <Modal isOpen={isOpen} onClose={close} title="Manage Teams" size="lg">
      <p className="mb-4 text-sm text-base-content/70">
        Multi-agent rosters shown in the AGENTS sidepane. These are not the
        Django LLM-profile aliases on <code>/v1/teams/</code>.
      </p>
      <ul className="space-y-3" aria-label="Team rosters">
        {teams.map((team) => (
          <li
            key={team.id}
            className="rounded-lg border border-base-300 bg-base-200/40 px-3 py-2"
          >
            <div className="flex items-start gap-2">
              <span className="os-team-mark mt-0.5" aria-hidden="true">
                <Users className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{team.name}</p>
                {team.description ? (
                  <p className="text-xs text-base-content/55">{team.description}</p>
                ) : null}
                {team.members.length === 0 ? (
                  <p className="mt-1 text-xs text-base-content/55">
                    No members yet — add members to enable send-to-all.
                  </p>
                ) : (
                  <ul className="mt-1 text-xs text-base-content/70">
                    {team.members.map((member) => (
                      <li key={member.id}>
                        {member.name}{' '}
                        <span className="text-base-content/45">
                          ({memberKindLabel(member)})
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-base-content/50">
        Drag-and-drop member editing may ship in a sibling PR. This overlay
        stays over chat so you are not ejected to the Django alias admin.
      </p>
      <div className="modal-action">
        <button type="button" className="btn btn-ghost btn-sm" onClick={close}>
          <X className="h-4 w-4" aria-hidden="true" />
          Close
        </button>
        <a href="/teams/" className="btn btn-ghost btn-sm">
          Django alias admin
        </a>
      </div>
    </Modal>
  )
}
