import { saveAvatarTheme } from '../lib/avatarTheme'
import { useAvatarTheme } from '../lib/useAvatarTheme'

export interface AvatarThemePickerProps {
  id?: string
}

/** Settings control: Blobs (default) or Bland static. Persists like hostname (REQ-155). */
export default function AvatarThemePicker({ id = 'os-avatar-theme' }: AvatarThemePickerProps) {
  const theme = useAvatarTheme()
  const selectValue = theme === 'default' ? 'bland' : theme

  return (
    <div className="flex w-full flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        Avatar theme
      </label>
      <select
        id={id}
        className="select select-bordered select-sm w-full"
        value={selectValue}
        onChange={(event) => {
          saveAvatarTheme(event.target.value)
        }}
      >
        <option value="blobs">Blobs with eyes (default)</option>
        <option value="bland">Bland static circle</option>
      </select>
      <p className="text-xs text-base-content/55">
        Blobs are per-agent shapes with eyes (default). Bland static uses identical grey circles.
        Custom uploaded faces always win. Generated still avatars from Settings → Image
        generation apply on Bland and stay unused while Blobs is selected.
      </p>
    </div>
  )
}
