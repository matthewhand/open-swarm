import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Users } from 'lucide-react'
import { Alert, Badge, Button, Input, Modal } from './DaisyUI'
import {
  createTeamRoster,
  fetchTeamAgents,
  fetchTeamRosters,
  updateTeamRoster,
  type TeamAgent,
  type TeamMemberRole,
  type TeamRoster,
  type TeamRosterMember,
} from '../lib/api'
import {
  addMember,
  agentDisplayName,
  DEFAULT_TEAM_WIRES,
  DRAG_MIME,
  emptyRosterDraft,
  encodeDragAgent,
  KIND_LABEL,
  parseDragAgent,
  PLACEHOLDER_TEAM_AGENTS,
  removeMember,
  rosterHasMember,
  setMemberRole,
  TEAM_MEMBER_ROLES,
} from '../lib/teamRoster'

export const OPEN_TEAM_COMPOSER_EVENT = 'swarm:open-team-composer'

interface ContextMenuState {
  mode: 'add' | 'remove'
  agent: TeamAgent
  x: number
  y: number
}

export interface TeamComposerProps {
  isOpen: boolean
  onClose: () => void
}

function kindBadgeType(kind: TeamAgent['kind']): 'info' | 'success' | 'warning' {
  if (kind === 'api') return 'info'
  if (kind === 'cli') return 'success'
  return 'warning'
}

export default function TeamComposer({ isOpen, onClose }: TeamComposerProps) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [members, setMembers] = useState<TeamRosterMember[]>([])
  const [wires, setWires] = useState({ ...DEFAULT_TEAM_WIRES })
  const [savedId, setSavedId] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [menu, setMenu] = useState<ContextMenuState | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  const agentsQuery = useQuery({
    queryKey: ['team-agents'],
    queryFn: fetchTeamAgents,
    enabled: isOpen,
    retry: 1,
  })
  const rostersQuery = useQuery({
    queryKey: ['team-rosters'],
    queryFn: fetchTeamRosters,
    enabled: isOpen,
    retry: 1,
  })

  const availableAgents = useMemo(() => {
    const data = agentsQuery.data?.data
    if (data && data.length > 0) return data
    if (agentsQuery.isError || (agentsQuery.isSuccess && (!data || data.length === 0))) {
      return PLACEHOLDER_TEAM_AGENTS
    }
    return data ?? []
  }, [agentsQuery.data, agentsQuery.isError, agentsQuery.isSuccess])

  const agentsByKind = useMemo(() => {
    return {
      api: availableAgents.filter((agent) => agent.kind === 'api'),
      cli: availableAgents.filter((agent) => agent.kind === 'cli'),
      remote: availableAgents.filter((agent) => agent.kind === 'remote'),
    }
  }, [availableAgents])

  const resetDraft = useCallback(() => {
    const draft = emptyRosterDraft()
    setName(draft.name)
    setMembers(draft.members)
    setWires({ ...draft.wires })
    setSavedId(null)
    setStatus(null)
  }, [])

  useEffect(() => {
    if (isOpen) resetDraft()
  }, [isOpen, resetDraft])

  const closeMenu = useCallback(() => setMenu(null), [])

  useEffect(() => {
    if (!menu) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMenu()
    }
    const onPointer = (event: Event) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        closeMenu()
      }
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('pointerdown', onPointer)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('pointerdown', onPointer)
    }
  }, [menu, closeMenu])

  const addFromAgent = useCallback((agent: TeamAgent) => {
    setMembers((prev) => addMember(prev, agent))
    setStatus(null)
    closeMenu()
  }, [closeMenu])

  const removeFromAgent = useCallback((agent: Pick<TeamRosterMember, 'kind' | 'id' | 'source'>) => {
    setMembers((prev) => removeMember(prev, agent))
    closeMenu()
  }, [closeMenu])

  const onDragStart = (event: React.DragEvent<HTMLElement>, agent: TeamAgent) => {
    try {
      event.dataTransfer.clearData('text/uri-list')
      event.dataTransfer.clearData('URL')
      event.dataTransfer.clearData('text/html')
    } catch {
      /* ignore */
    }
    event.dataTransfer.setData(DRAG_MIME, encodeDragAgent(agent))
    event.dataTransfer.setData('text/plain', encodeDragAgent(agent))
    event.dataTransfer.effectAllowed = 'copy'
    try {
      event.dataTransfer.clearData('text/uri-list')
      event.dataTransfer.clearData('URL')
      event.dataTransfer.clearData('text/html')
    } catch {
      /* ignore */
    }
  }

  const onDragOver = (event: React.DragEvent<HTMLElement>) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
    setDragOver(true)
  }

  const onDragLeave = (event: React.DragEvent<HTMLElement>) => {
    if (event.currentTarget.contains(event.relatedTarget as Node)) return
    setDragOver(false)
  }

  const onDrop = (event: React.DragEvent<HTMLElement>) => {
    event.preventDefault()
    setDragOver(false)
    const raw = event.dataTransfer.getData(DRAG_MIME) || event.dataTransfer.getData('text/plain')
    const agent = parseDragAgent(raw)
    if (agent) addFromAgent(agent)
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const trimmed = name.trim()
      if (!trimmed) {
        throw new Error('Team name is required.')
      }
      const payload = { name: trimmed, members, wires }
      if (savedId) {
        return updateTeamRoster(savedId, payload)
      }
      return createTeamRoster(payload)
    },
    onSuccess: (roster: TeamRoster) => {
      setSavedId(roster.id)
      setName(roster.name)
      queryClient.invalidateQueries({ queryKey: ['team-rosters'] })
      setStatus(`Saved roster “${roster.name}” to team_rosters.json.`)
    },
  })

  const loadRoster = (roster: TeamRoster) => {
    setSavedId(roster.id)
    setName(roster.name)
    setMembers(roster.members)
    setWires({
      handoff: roster.wires?.handoff ?? true,
      as_tool: roster.wires?.as_tool ?? true,
    })
    setStatus(null)
  }

  const savedRosters = rostersQuery.data?.data ?? []

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New team"
      size="2xl"
      className="max-h-[90vh] overflow-y-auto"
    >
      <div className="space-y-4">
        <p className="text-sm text-base-content/60">
          Compose a roster of API, CLI, and remote members. Django{' '}
          <a className="link" href="/teams/">
            /teams/
          </a>{' '}
          still edits LLM-profile aliases in teams.json — this overlay writes{' '}
          <code className="text-xs">team_rosters.json</code>.
        </p>

        <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
          <Input
            label="Team name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="research-squad"
            size="sm"
          />
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={resetDraft}>
              New
            </Button>
            <Button
              type="button"
              size="sm"
              loading={saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              Save roster
            </Button>
          </div>
        </div>

        {savedRosters.length > 0 && (
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Saved rosters</span>
            <select
              className="select select-sm"
              value={savedId ?? ''}
              onChange={(event) => {
                const next = savedRosters.find((row) => row.id === event.target.value)
                if (next) loadRoster(next)
                else resetDraft()
              }}
              aria-label="Saved rosters"
            >
              <option value="">New team</option>
              {savedRosters.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <fieldset className="rounded-lg border border-base-300 bg-base-200/40 px-3 py-2">
          <legend className="px-1 text-xs font-semibold uppercase tracking-[0.08em] text-base-content/45">
            Wires
          </legend>
          <div className="flex flex-wrap gap-6">
            <label className="label cursor-pointer justify-start gap-2">
              <input
                type="checkbox"
                className="toggle toggle-sm"
                checked={wires.handoff}
                onChange={(event) =>
                  setWires((prev) => ({ ...prev, handoff: event.target.checked }))
                }
              />
              <span className="label-text">handoff</span>
            </label>
            <label className="label cursor-pointer justify-start gap-2">
              <input
                type="checkbox"
                className="toggle toggle-sm"
                checked={wires.as_tool}
                onChange={(event) =>
                  setWires((prev) => ({ ...prev, as_tool: event.target.checked }))
                }
              />
              <span className="label-text">as_tool</span>
            </label>
          </div>
          <p className="mt-2 text-xs text-base-content/50">
            Per-team openai-agents wiring. Both default on. Gate is unwired — all tools
            are approved.
          </p>
        </fieldset>

        {saveMutation.isError && (
          <Alert type="error">
            {saveMutation.error instanceof Error
              ? saveMutation.error.message
              : 'Failed to save roster.'}
          </Alert>
        )}
        {status && (
          <Alert type="success">{status}</Alert>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <section
            aria-label="Team roster drop zone"
            data-testid="team-drop-zone"
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            className={`min-h-[18rem] rounded-xl border-2 border-dashed px-4 py-4 transition-colors ${
              dragOver
                ? 'border-primary bg-base-200'
                : 'border-base-content/25 bg-base-200/70'
            }`}
          >
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-base-content/70">
              <Users className="h-4 w-4" aria-hidden="true" />
              Roster
            </div>
            {members.length === 0 ? (
              <div className="flex h-[13rem] flex-col items-center justify-center text-center text-base-content/45">
                <p className="text-sm font-medium tracking-wide">drop agents here</p>
                <p className="mt-1 max-w-xs text-xs">
                  Drag from the available list, or use the context menu Add action.
                </p>
              </div>
            ) : (
              <ul className="flex flex-col gap-2 os-scrollable-picker-list pr-1" aria-label="Roster members">
                {members.map((member) => {
                  const agent: TeamAgent = {
                    id: member.id,
                    name: member.id,
                    kind: member.kind,
                    source: member.source,
                  }
                  return (
                    <li key={`${member.kind}:${member.source}`}>
                      <article
                        className="flex flex-wrap items-center gap-2 rounded-lg border border-base-300 bg-base-100 px-3 py-2"
                        onContextMenu={(event) => {
                          event.preventDefault()
                          setMenu({
                            mode: 'remove',
                            agent,
                            x: event.clientX,
                            y: event.clientY,
                          })
                        }}
                      >
                        <span className="font-medium">{agentDisplayName(member)}</span>
                        <Badge type={kindBadgeType(member.kind)} size="sm">
                          {KIND_LABEL[member.kind]}
                        </Badge>
                        <label className="sr-only" htmlFor={`role-${member.kind}-${member.id}`}>
                          Role for {member.id}
                        </label>
                        <select
                          id={`role-${member.kind}-${member.id}`}
                          className="select select-xs"
                          value={member.role}
                          onChange={(event) =>
                            setMembers((prev) =>
                              setMemberRole(
                                prev,
                                member,
                                event.target.value as TeamMemberRole,
                              ),
                            )
                          }
                        >
                          {TEAM_MEMBER_ROLES.map((role) => (
                            <option key={role} value={role}>
                              {role}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs ml-auto"
                          onClick={() => removeFromAgent(member)}
                        >
                          Remove
                        </button>
                      </article>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          <section aria-label="Available agents" className="min-h-[18rem]">
            <div className="mb-3 text-sm font-medium text-base-content/70">Available agents</div>
            {agentsQuery.isPending && availableAgents.length === 0 ? (
              <p className="text-sm text-base-content/45">Loading agents…</p>
            ) : (
              <div
                className="flex max-h-[22rem] flex-col gap-3 overflow-y-auto pr-1"
                aria-label="Available agents list"
                role="list"
              >
                {(['api', 'cli', 'remote'] as const).map((kind) => (
                  <div key={kind} className="min-h-0">
                    <h4 className="mb-1 text-xs font-semibold uppercase tracking-[0.08em] text-base-content/45">
                      {KIND_LABEL[kind]}
                      <span className="ml-1 font-normal normal-case tracking-normal text-base-content/35">
                        ({agentsByKind[kind].length})
                      </span>
                    </h4>
                    <ul
                      className="flex flex-col gap-1 os-scrollable-picker-list max-h-40 overflow-y-auto pr-1"
                    >
                      {agentsByKind[kind].length === 0 ? (
                        <li className="px-2 py-1 text-xs text-base-content/40">None</li>
                      ) : (
                        agentsByKind[kind].map((agent) => {
                          const already = rosterHasMember(members, agent)
                          return (
                            <li
                              key={`${agent.kind}:${agent.source}`}
                              draggable
                              onDragStart={(event) => onDragStart(event, agent)}
                              onContextMenu={(event) => {
                                event.preventDefault()
                                setMenu({
                                  mode: already ? 'remove' : 'add',
                                  agent,
                                  x: event.clientX,
                                  y: event.clientY,
                                })
                              }}
                              className="flex cursor-grab items-center gap-2 rounded-lg border border-base-300 bg-base-100 px-3 py-2 active:cursor-grabbing"
                            >
                              <div className="flex w-full items-center gap-2">
                                <span className="min-w-0 flex-1 truncate font-medium">
                                  {agentDisplayName(agent)}
                                </span>
                                <Badge type={kindBadgeType(agent.kind)} size="sm">
                                  {KIND_LABEL[agent.kind]}
                                </Badge>
                                {agent.placeholder && (
                                  <Badge type="ghost" size="xs">
                                    placeholder
                                  </Badge>
                                )}
                                <button
                                  type="button"
                                  className="btn btn-ghost btn-xs"
                                  disabled={already}
                                  onClick={() => addFromAgent(agent)}
                                >
                                  Add
                                </button>
                              </div>
                            </li>
                          )
                        })
                      )}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {menu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Actions for ${agentDisplayName(menu.agent)}`}
          className="fixed z-[80] min-w-[10rem] rounded-lg border border-base-300 bg-neutral py-1 text-sm shadow-xl"
          style={{ left: menu.x, top: menu.y }}
        >
          {menu.mode === 'add' ? (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50"
              onClick={() => addFromAgent(menu.agent)}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Add
            </button>
          ) : (
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-base-300/50"
              onClick={() => removeFromAgent(menu.agent)}
            >
              Remove
            </button>
          )}
        </div>
      )}
    </Modal>
  )
}
