import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

interface EditableFieldProps {
  value: string
  label: string
  onSave: (next: string) => void
  className?: string
  inputClassName?: string
  allowEmpty?: boolean
}

/** Click-to-edit text using daisyUI inputs — no extra UI kit. */
export function EditableField({
  value,
  label,
  onSave,
  className = '',
  inputClassName = '',
  allowEmpty = false,
}: EditableFieldProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const ref = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!editing) setDraft(value)
  }, [value, editing])

  useEffect(() => {
    if (editing) {
      ref.current?.focus()
      ref.current?.select()
    }
  }, [editing])

  const commit = () => {
    const next = draft.trim()
    if (!next && !allowEmpty) {
      setDraft(value)
      setEditing(false)
      return
    }
    if (next !== value) onSave(next)
    setEditing(false)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      commit()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setDraft(value)
      setEditing(false)
    }
  }

  if (editing) {
    return (
      <input
        ref={ref}
        aria-label={`Edit ${label}`}
        className={`input input-xs input-bordered h-6 min-h-0 px-1.5 w-full max-w-[14rem] ${inputClassName}`}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={onKeyDown}
      />
    )
  }

  return (
    <button
      type="button"
      className={`text-left truncate rounded-sm hover:bg-base-200/80 px-0.5 -mx-0.5 cursor-text ${className}`}
      aria-label={`Click to edit ${label}`}
      title={`Click to edit ${label}`}
      onClick={() => setEditing(true)}
    >
      {value || `Add ${label}`}
    </button>
  )
}
