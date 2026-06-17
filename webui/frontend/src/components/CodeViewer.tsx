import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'

/** Match the app's DaisyUI theme (App sets data-theme on a wrapper div). */
function isDark(): boolean {
  if (typeof document === 'undefined') return false
  return !!document.querySelector('[data-theme="dark"]')
}

/** Read-only, syntax-highlighted code view. Lazy-loaded to keep CodeMirror out
 * of the main bundle. */
export default function CodeViewer({ value, height = '420px' }: { value: string; height?: string }) {
  return (
    <CodeMirror
      value={value}
      height={height}
      theme={isDark() ? 'dark' : 'light'}
      extensions={[python()]}
      editable={false}
      basicSetup={{ lineNumbers: true, foldGutter: true, highlightActiveLine: false }}
    />
  )
}
