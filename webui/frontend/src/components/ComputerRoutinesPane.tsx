import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, GitMerge, Plus } from 'lucide-react'
import { Button, Input, Select, Textarea } from './DaisyUI'
import {
  createRoutine,
  deleteRoutine,
  fetchRoutines,
  formatRoutineHistoryTime,
  ROUTINE_ACTOR_ANYONE,
  ROUTINE_EVENT_MERGED,
  ROUTINE_TRIGGER_GITHUB_PR_MERGED,
  testRunRoutine,
  triggerSummary,
  updateRoutine,
  type Routine,
} from '../lib/routines'

export interface ComputerRoutinesPaneProps {
  agentId: string
  agentName: string
  /** True only when a real computer-control session exists. Tests stay false. */
  hasScreenSession?: boolean
  nowMs?: number
}

type PaneView = 'list' | 'editor'

export function ComputerRoutinesPane({
  agentId,
  agentName,
  hasScreenSession = false,
  nowMs,
}: ComputerRoutinesPaneProps) {
  const [view, setView] = useState<PaneView>('list')
  const [routines, setRoutines] = useState<Routine[]>([])
  const [editing, setEditing] = useState<Routine | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const screenCaption = `${agentName || 'Agent'}'s screen`

  const load = async () => {
    if (!agentId) {
      setRoutines([])
      return
    }
    try {
      setRoutines(await fetchRoutines(agentId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load routines.')
    }
  }

  useEffect(() => {
    void load()
    // Reload when the selected agent changes; stay on the list.
    setView('list')
    setEditing(null)
    setConfirmDelete(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId])

  const openEditor = (routine: Routine) => {
    setEditing(routine)
    setConfirmDelete(false)
    setError(null)
    setView('editor')
  }

  const backToList = async () => {
    setView('list')
    setEditing(null)
    setConfirmDelete(false)
    await load()
  }

  const onAdd = async () => {
    if (!agentId || busy) return
    setBusy(true)
    setError(null)
    try {
      const created = await createRoutine(agentId, { name: 'New routine' })
      setRoutines((prev) => [...prev, created])
      openEditor(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create routine.')
    } finally {
      setBusy(false)
    }
  }

  const onSaveField = async (patch: Parameters<typeof updateRoutine>[2]) => {
    if (!agentId || !editing) return
    try {
      const updated = await updateRoutine(agentId, editing.id, patch)
      setEditing(updated)
      setRoutines((prev) => prev.map((row) => (row.id === updated.id ? updated : row)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save routine.')
    }
  }

  const onTestRun = async () => {
    if (!agentId || !editing || busy) return
    setBusy(true)
    setError(null)
    try {
      const updated = await testRunRoutine(agentId, editing.id)
      setEditing(updated)
      setRoutines((prev) => prev.map((row) => (row.id === updated.id ? updated : row)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test run failed.')
    } finally {
      setBusy(false)
    }
  }

  const onDelete = async () => {
    if (!agentId || !editing) return
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setBusy(true)
    try {
      await deleteRoutine(agentId, editing.id)
      await backToList()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete routine.')
    } finally {
      setBusy(false)
    }
  }

  const history = useMemo(() => {
    const rows = [...(editing?.history ?? [])]
    rows.sort((a, b) => String(b.ran_at).localeCompare(String(a.ran_at)))
    return rows
  }, [editing])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4" data-testid="computer-routines-pane">
      {error ? (
        <p className="text-sm text-error" role="alert">
          {error}
        </p>
      ) : null}

      {view === 'list' ? (
        <>
          <figure className="space-y-2" data-testid="agent-screen-thumbnail">
            <div
              className="flex aspect-video w-full items-center justify-center rounded-box border border-base-300 bg-base-200 text-sm text-base-content/60"
              role="img"
              aria-label={screenCaption}
            >
              {hasScreenSession
                ? 'Last frame'
                : 'No screen session'}
            </div>
            <figcaption className="text-sm text-base-content/70">{screenCaption}</figcaption>
          </figure>

          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-semibold">Routines</h3>
            <button
              type="button"
              className="btn btn-ghost btn-sm btn-square"
              aria-label="Add routine"
              onClick={() => void onAdd()}
              disabled={busy || !agentId}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          {routines.length === 0 ? (
            <p className="text-sm text-base-content/60">No routines yet.</p>
          ) : (
            <ul className="menu w-full rounded-box bg-base-200 p-0">
              {routines.map((routine) => (
                <li key={routine.id}>
                  <button
                    type="button"
                    className="flex items-start gap-3 text-left"
                    onClick={() => openEditor(routine)}
                  >
                    <GitMerge className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <span className="min-w-0">
                      <span className="block font-medium">{routine.name}</span>
                      <span className="block text-xs text-base-content/60">
                        {routine.when_to_run || triggerSummary(routine.trigger)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : editing ? (
        <div className="flex min-h-0 flex-1 flex-col gap-4" data-testid="routine-editor">
          <div className="flex items-center justify-between gap-2">
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void backToList()}>
              Back
            </button>
            <h3 className="text-base font-semibold">Routine</h3>
            <span className="w-16" aria-hidden="true" />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <span>Active</span>
              <input
                type="checkbox"
                className="toggle toggle-sm"
                role="switch"
                aria-label="Active"
                checked={editing.active}
                onChange={(event) => void onSaveField({ active: event.target.checked })}
              />
            </label>
            <Button type="button" size="sm" variant="ghost" onClick={() => void onTestRun()} disabled={busy}>
              Test run
            </Button>
            <Button type="button" size="sm" color="error" variant="ghost" onClick={() => void onDelete()}>
              {confirmDelete ? 'Confirm delete' : 'Delete'}
            </Button>
          </div>

          <Input
            label="Name"
            size="sm"
            value={editing.name}
            onChange={(event) => setEditing({ ...editing, name: event.target.value })}
            onBlur={(event) => void onSaveField({ name: event.target.value })}
          />
          <Textarea
            label="Instruction"
            size="sm"
            rows={4}
            value={editing.instruction}
            onChange={(event) => setEditing({ ...editing, instruction: event.target.value })}
            onBlur={(event) => void onSaveField({ instruction: event.target.value })}
          />

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">When to run</legend>
            <Select
              label="Trigger"
              size="sm"
              value={ROUTINE_TRIGGER_GITHUB_PR_MERGED}
              onChange={() => undefined}
            >
              <option value={ROUTINE_TRIGGER_GITHUB_PR_MERGED}>When a PR merges</option>
            </Select>
            <Input
              label="Repository"
              size="sm"
              placeholder="owner/repo"
              value={editing.trigger.owner_repo}
              onChange={(event) =>
                setEditing({
                  ...editing,
                  trigger: { ...editing.trigger, owner_repo: event.target.value },
                })
              }
              onBlur={(event) =>
                void onSaveField({
                  trigger: { ...editing.trigger, owner_repo: event.target.value },
                })
              }
            />
            <Input label="Event" size="sm" value="Merged" readOnly />
            <Input
              label="Actor"
              size="sm"
              value={editing.trigger.actor || ROUTINE_ACTOR_ANYONE}
              onChange={(event) =>
                setEditing({
                  ...editing,
                  trigger: { ...editing.trigger, actor: event.target.value || ROUTINE_ACTOR_ANYONE },
                })
              }
              onBlur={(event) =>
                void onSaveField({
                  trigger: {
                    ...editing.trigger,
                    actor: event.target.value || ROUTINE_ACTOR_ANYONE,
                    event: ROUTINE_EVENT_MERGED,
                  },
                })
              }
            />
          </fieldset>

          <section aria-label="Routine history" className="space-y-2">
            <h4 className="text-sm font-medium">History</h4>
            {history.length === 0 ? (
              <p className="text-sm text-base-content/60">No successful runs yet.</p>
            ) : (
              <ul className="space-y-2">
                {history.map((row) => (
                  <li key={row.id} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />
                    <span>{formatRoutineHistoryTime(row.ran_at, nowMs)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </div>
  )
}

export default ComputerRoutinesPane
