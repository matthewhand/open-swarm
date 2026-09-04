import { saveAvatarTheme } from '../lib/avatarTheme'
import { useAvatarTheme } from '../lib/useAvatarTheme'

export interface AvatarThemePickerProps {
  id?: string
}

/** Settings control: Default (current dots) or Blobs. Persists like hostname. */
export default function AvatarThemePicker({ id = 'os-avatar-theme' }: AvatarThemePickerProps) {
  const theme = useAvatarTheme()

  return (
    <div className="flex w-full flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        Avatar theme
      </label>
      <select
        id={id}
        className="select select-bordered select-sm w-full"
        value={theme}
        onChange={(event) => {
          saveAvatarTheme(event.target.value)
        }}
      >
        <option value="default">Default</option>
        <option value="blobs">Blobs</option>
      </select>
      <p className="text-xs text-base-content/55">
        Default keeps the current marks. Blobs are per-agent shapes with eyes.
        This does not rewrite blueprints.
      </p>
    </div>
  )
}
