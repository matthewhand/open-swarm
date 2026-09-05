/**
 * REQ-85: clickable suggestion chips. DaisyUI controls, not assistant bubbles.
 */

export function SuggestionChips({
  chips,
  disabled = false,
  onChoose,
}: {
  chips: readonly string[]
  disabled?: boolean
  onChoose: (value: string) => void
}) {
  if (chips.length === 0) return null
  return (
    <div
      className="os-suggestion-chips"
      role="group"
      aria-label="Suggested messages"
      data-testid="suggestion-chips"
    >
      {chips.map((chip) => (
        <button
          key={chip}
          type="button"
          className="btn btn-soft btn-sm os-suggestion-chip"
          disabled={disabled}
          data-testid="suggestion-chip"
          data-suggestion-chip={chip}
          onClick={() => {
            if (disabled) return
            onChoose(chip)
          }}
        >
          {chip}
        </button>
      ))}
    </div>
  )
}
