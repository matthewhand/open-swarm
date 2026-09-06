import { useEffect, useId, useMemo, useState } from 'react'
import { Button, Input, Select } from './DaisyUI'
import type { AgentRole } from '../lib/api'
import {
  MAILBOX_ACL_ENTRY_KINDS,
  MAILBOX_ACL_ROLE_OPTIONS,
  defaultMailboxAcl,
  fetchMailboxAcl,
  fetchMailboxAclRole,
  isAllowAllRole,
  resetMailboxAcl,
  saveMailboxAcl,
  type MailboxAcl,
  type MailboxAclEntry,
  type MailboxAclEntryKind,
  type MailboxAclMode,
  type MailboxAclScope,
} from '../lib/mailboxAcl'

export interface MailboxAclEditorProps {
  agentId: string
  role: AgentRole
}

/**
 * Per-agent (or per-role) whitelist XOR blacklist for list_agents / send_message.
 * Support defaults to whitelist everything. DaisyUI 5 + React 18.
 */
export default function MailboxAclEditor({ agentId, role }: MailboxAclEditorProps) {
  const modeToggleId = useId()
  const [scope, setScope] = useState<MailboxAclScope>('agent')
  const [acl, setAcl] = useState<MailboxAcl>(() => defaultMailboxAcl(agentId, role, 'agent'))
  const [entryKind, setEntryKind] = useState<MailboxAclEntryKind>('agent')
  const [entryId, setEntryId] = useState('')

  const chooseKind = (next: MailboxAclEntryKind) => {
    setEntryKind(next)
    setEntryId(next === 'role' ? 'support' : '')
  }
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const targetId = scope === 'role' ? role : agentId

  useEffect(() => {
    if (!agentId) return
    let cancelled = false
    setError(null)
    ;(async () => {
      const next =
        scope === 'role' ? await fetchMailboxAclRole(role) : await fetchMailboxAcl(agentId, role)
      if (!cancelled) setAcl(next)
    })()
    return () => {
      cancelled = true
    }
  }, [agentId, role, scope])

  const persist = async (next: { mode: MailboxAclMode; entries: MailboxAclEntry[] }) => {
    if (!targetId) return
    setBusy(true)
    setError(null)
    try {
      const saved = await saveMailboxAcl(scope, targetId, { ...next, role })
      setAcl(saved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save mailbox ACL.')
    } finally {
      setBusy(false)
    }
  }

  const toggleMode = (nextMode: MailboxAclMode) => {
    if (nextMode === acl.mode) return
    void persist({ mode: nextMode, entries: acl.entries })
  }

  const addEntry = () => {
    const id = entryId.trim()
    if (!id) return
    const nextEntry: MailboxAclEntry = { kind: entryKind, id }
    if (acl.entries.some((row) => row.kind === nextEntry.kind && row.id === nextEntry.id)) {
      setEntryId('')
      return
    }
    setEntryId('')
    void persist({ mode: acl.mode, entries: [...acl.entries, nextEntry] })
  }

  const removeEntry = (entry: MailboxAclEntry) => {
    void persist({
      mode: acl.mode,
      entries: acl.entries.filter((row) => !(row.kind === entry.kind && row.id === entry.id)),
    })
  }

  const reset = async () => {
    if (!targetId) return
    setBusy(true)
    setError(null)
    try {
      const next = await resetMailboxAcl(scope, targetId, role)
      setAcl(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reset mailbox ACL.')
    } finally {
      setBusy(false)
    }
  }

  const kindHint = useMemo(
    () => MAILBOX_ACL_ENTRY_KINDS.find((row) => row.kind === entryKind)?.hint || '',
    [entryKind],
  )
  const supportDefault = isAllowAllRole(role) && acl.mode === 'whitelist' && acl.entries.length === 0

  return (
    <section
      className="space-y-3 rounded-box border border-base-300 bg-base-200/40 p-3"
      data-testid="mailbox-acl-editor"
    >
      <div>
        <h3 className="text-sm font-semibold text-base-content/80">Mailbox visibility</h3>
        <p className="text-xs text-base-content/60 mt-0.5">
          Who this seat may <code>list_agents</code> / <code>send_message</code>. Toggle
          whitelist or blacklist. Entries target an <strong>agent</strong> id, a{' '}
          <strong>team</strong> roster, or a <strong>role</strong>. Support is whitelist
          everything by default.
        </p>
      </div>

      <div className="flex flex-wrap gap-3" role="radiogroup" aria-label="ACL scope">
        <label className="label cursor-pointer gap-2 py-0">
          <input
            type="radio"
            className="radio radio-sm radio-primary"
            name="mailbox-acl-scope"
            value="agent"
            checked={scope === 'agent'}
            onChange={() => setScope('agent')}
          />
          <span className="label-text text-sm">This agent</span>
        </label>
        <label className="label cursor-pointer gap-2 py-0">
          <input
            type="radio"
            className="radio radio-sm radio-primary"
            name="mailbox-acl-scope"
            value="role"
            checked={scope === 'role'}
            onChange={() => setScope('role')}
          />
          <span className="label-text text-sm">Role ({role})</span>
        </label>
      </div>

      <label
        htmlFor={modeToggleId}
        className="label cursor-pointer items-center justify-between gap-4 rounded-box border border-base-300 bg-base-100/70 px-3 py-2"
      >
        <span className="label-text text-sm font-semibold">
          {acl.mode === 'whitelist' ? 'Whitelist' : 'Blacklist'}
        </span>
        <span className="flex items-center gap-2 text-xs text-base-content/60">
          White
          <input
            id={modeToggleId}
            type="checkbox"
            className="toggle toggle-primary toggle-sm"
            role="switch"
            aria-label="Toggle whitelist or blacklist"
            checked={acl.mode === 'blacklist'}
            disabled={!targetId || busy}
            onChange={(event) => toggleMode(event.target.checked ? 'blacklist' : 'whitelist')}
          />
          Black
        </span>
      </label>

      {supportDefault ? (
        <p className="text-xs text-base-content/70" data-testid="mailbox-acl-allow-all">
          Support allow-all: every same-kind peer is visible until you add a
          whitelist entry or switch to blacklist.
        </p>
      ) : null}

      {acl.inherited && scope === 'agent' ? (
        <p className="text-xs text-base-content/55" data-testid="mailbox-acl-inherited">
          Inheriting the {acl.source === 'role' ? `${role} role` : 'default'} policy.
          Add or toggle to override this agent.
        </p>
      ) : null}

      <ul className="space-y-1" data-testid="mailbox-acl-entries">
        {acl.entries.length === 0 ? (
          <li className="text-xs text-base-content/55">No list entries yet.</li>
        ) : (
          acl.entries.map((entry) => (
            <li
              key={`${entry.kind}:${entry.id}`}
              className="flex items-center justify-between gap-2 rounded-box border border-base-300 bg-base-100/80 px-2 py-1"
            >
              <span className="min-w-0 truncate text-sm">
                <span className="badge badge-sm badge-ghost mr-2">{entry.kind}</span>
                {entry.id}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="xs"
                disabled={busy}
                aria-label={`Remove ${entry.kind} ${entry.id}`}
                onClick={() => removeEntry(entry)}
              >
                Remove
              </Button>
            </li>
          ))
        )}
      </ul>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[8rem_1fr_auto] sm:items-end">
        <Select
          label="Entry kind"
          name="mailbox-acl-entry-kind"
          size="sm"
          value={entryKind}
          onChange={(event) => chooseKind(event.target.value as MailboxAclEntryKind)}
        >
          {MAILBOX_ACL_ENTRY_KINDS.map((row) => (
            <option key={row.kind} value={row.kind}>
              {row.label}
            </option>
          ))}
        </Select>
        {entryKind === 'role' ? (
          <Select
            label="Role"
            name="mailbox-acl-entry-role"
            size="sm"
            value={MAILBOX_ACL_ROLE_OPTIONS.some((row) => row.value === entryId) ? entryId : 'support'}
            onChange={(event) => setEntryId(event.target.value)}
          >
            {MAILBOX_ACL_ROLE_OPTIONS.map((row) => (
              <option key={row.value} value={row.value}>
                {row.label}
              </option>
            ))}
          </Select>
        ) : (
          <Input
            label={entryKind === 'team' ? 'Team id' : 'Agent id'}
            name="mailbox-acl-entry-id"
            size="sm"
            value={entryId}
            onChange={(event) => setEntryId(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            placeholder={entryKind === 'team' ? 'office' : 'ada'}
          />
        )}
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={busy || !entryId.trim()}
          onClick={addEntry}
        >
          Add
        </Button>
      </div>
      <p className="text-xs text-base-content/55">{kindHint}</p>

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="ghost" size="xs" disabled={busy} onClick={() => void reset()}>
          Reset to default
        </Button>
      </div>

      {error ? (
        <p className="text-xs text-error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  )
}
