import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { EditorView } from '@codemirror/view'

// Give CodeMirror's editable region (.cm-content, role=textbox) an accessible
// name so screen readers announce it (axe: aria-input-field-name).
const a11yLabel = EditorView.contentAttributes.of({
  'aria-label': 'Blueprint source code (read-only)',
})

// The @uiw dark theme's gutter line numbers (#7d8799 on #282c34 = 3.86:1) fail
// WCAG AA; lift them to a passing contrast in dark mode only.
const darkGutterContrast = EditorView.theme({ '.cm-gutterElement': { color: '#aeb6c2' } })

/** Match the app's DaisyUI theme (App sets data-theme on a wrapper div). */
function isDark(): boolean {
  if (typeof document === 'undefined') return false
  return !!document.querySelector('[data-theme="dark"]')
}

/** Read-only, syntax-highlighted code view. Lazy-loaded to keep CodeMirror out
 * of the main bundle. */
export default function CodeViewer({ value, height = '420px' }: { value: string; height?: string }) {
  const dark = isDark()
  return (
    <CodeMirror
      value={value}
      height={height}
      theme={dark ? 'dark' : 'light'}
      extensions={dark ? [python(), a11yLabel, darkGutterContrast] : [python(), a11yLabel]}
      readOnly
      onCreateEditor={(view) => {
        // Make the scroll container keyboard-reachable + named
        // (axe: scrollable-region-focusable).
        view.scrollDOM.setAttribute('tabindex', '0')
        view.scrollDOM.setAttribute('role', 'region')
        view.scrollDOM.setAttribute('aria-label', 'Blueprint source code (read-only)')
      }}
    />
  )
}
