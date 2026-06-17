import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'

/** Read-only, syntax-highlighted code view. Lazy-loaded to keep CodeMirror out
 * of the main bundle. */
export default function CodeViewer({ value, height = '420px' }: { value: string; height?: string }) {
  return (
    <CodeMirror
      value={value}
      height={height}
      extensions={[python()]}
      editable={false}
      basicSetup={{ lineNumbers: true, foldGutter: true, highlightActiveLine: false }}
    />
  )
}
