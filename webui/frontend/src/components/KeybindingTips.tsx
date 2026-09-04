import { useCallback, useState } from 'react'
import { X } from 'lucide-react'
import {
  dismissKeybindingTips,
  isKeybindingTipsDismissed,
  pinsShortcutLabel,
  searchShortcutLabel,
} from '../lib/keybindingTips'

/**
 * Quiet first-load keybinding row (REQ-160 / #571).
 * Same tip content + localStorage dismiss as #547, without the rail alert banner.
 */
export default function KeybindingTips() {
  const [dismissed, setDismissed] = useState(isKeybindingTipsDismissed)

  const onDismiss = useCallback(() => {
    dismissKeybindingTips()
    setDismissed(true)
  }, [])

  if (dismissed) return null

  return (
    <div
      className="os-keybinding-tips"
      data-testid="first-load-tips"
      aria-label="Keyboard tips"
    >
      <span className="os-search-tip">
        <kbd className="kbd kbd-xs">{searchShortcutLabel()}</kbd> Search
      </span>
      <span className="os-search-tip">
        <kbd className="kbd kbd-xs">{pinsShortcutLabel()}</kbd> Pins
      </span>
      <span className="os-search-tip">
        <kbd className="kbd kbd-xs">Esc</kbd> Clear
      </span>
      <button
        type="button"
        className="os-keybinding-tips__dismiss"
        aria-label="Dismiss tips"
        onClick={onDismiss}
      >
        <X className="h-3 w-3" aria-hidden="true" />
      </button>
    </div>
  )
}
