import { Info } from 'lucide-react'

/** A small info icon with a DaisyUI tooltip and a screen-reader label. */
export function InfoTip({ text }: { text: string }) {
  return (
    <span
      className="tooltip tooltip-right align-middle before:max-w-[18rem] before:whitespace-normal before:text-xs"
      data-tip={text}
    >
      <Info className="h-3.5 w-3.5 opacity-60" aria-label={text} />
    </span>
  )
}
