import { saveAvatarTheme } from '../lib/avatarTheme'
import { useAvatarTheme } from '../lib/useAvatarTheme'

export interface AvatarThemePickerProps {
  id?: string
}

/** Settings control: Blobs (default), Bland static, or Bee brand marks. Persists like hostname (REQ-155 / #801). */
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
        <option value="bee">Bee</option>
      </select>
      <p className="text-xs text-base-content/55">
        Blobs are per-agent shapes with eyes (default). Bland static uses identical grey circles.
        Bee is an optional choice: geometric WebUI brand marks — side-on and face-only, with
        googly eyes — assigned per agent. Existing users stay on their current theme.
        Custom uploaded faces always win. Generated still avatars from Settings → Image
        generation apply on Bland and stay unused while Blobs or Bee is selected.
      </p>
    </div>
  )
}
