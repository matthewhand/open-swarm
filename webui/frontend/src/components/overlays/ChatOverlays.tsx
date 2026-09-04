import { useEffect, useState } from 'react'
import {
  OPEN_BLUEPRINTS_EVENT,
  OPEN_COMPUTER_CONTROL_EVENT,
  OPEN_LLM_PROFILES_EVENT,
  OPEN_ROLE_PANE_EVENT,
  OPEN_SETTINGS_EVENT,
  OPEN_TEAMS_EVENT,
  type RolePaneDetail,
} from '../../lib/chromeOverlay'
import { DEFAULT_ROLE_ID } from './RoleDefinitionPane'
import type { SettingsSection } from './SettingsSheet'
import BlueprintsSheet from './BlueprintsSheet'
import ComputerControlSheet from './ComputerControlSheet'
import RolePaneSheet from './RolePaneSheet'
import SettingsSheet from './SettingsSheet'
import TeamsSheet from './TeamsSheet'

type OverlayId = 'settings' | 'teams' | 'blueprints' | 'role' | 'computer-control' | null

/**
 * Host for manage/settings sheets. Mounted beside Chat so opening any overlay
 * never swaps the React route or unmounts the conversation.
 */
export default function ChatOverlays() {
  const [overlay, setOverlay] = useState<OverlayId>(null)
  const [settingsSection, setSettingsSection] = useState<SettingsSection>('retention')
  const [roleId, setRoleId] = useState(DEFAULT_ROLE_ID)

  useEffect(() => {
    const openSettings = (section: SettingsSection = 'retention') => {
      setSettingsSection(section)
      setOverlay('settings')
    }
    const onSettings = () => openSettings('retention')
    const onLlm = () => openSettings('llm-profiles')
    const onTeams = () => setOverlay('teams')
    const onBlueprints = () => setOverlay('blueprints')
    const onComputer = () => setOverlay('computer-control')
    const onRole = (event: Event) => {
      const detail = (event as CustomEvent<RolePaneDetail>).detail
      const next = typeof detail?.roleId === 'string' && detail.roleId.trim()
        ? detail.roleId.trim()
        : DEFAULT_ROLE_ID
      setRoleId(next)
      setOverlay('role')
    }

    window.addEventListener(OPEN_SETTINGS_EVENT, onSettings)
    window.addEventListener(OPEN_LLM_PROFILES_EVENT, onLlm)
    window.addEventListener(OPEN_TEAMS_EVENT, onTeams)
    window.addEventListener(OPEN_BLUEPRINTS_EVENT, onBlueprints)
    window.addEventListener(OPEN_COMPUTER_CONTROL_EVENT, onComputer)
    window.addEventListener(OPEN_ROLE_PANE_EVENT, onRole)
    return () => {
      window.removeEventListener(OPEN_SETTINGS_EVENT, onSettings)
      window.removeEventListener(OPEN_LLM_PROFILES_EVENT, onLlm)
      window.removeEventListener(OPEN_TEAMS_EVENT, onTeams)
      window.removeEventListener(OPEN_BLUEPRINTS_EVENT, onBlueprints)
      window.removeEventListener(OPEN_COMPUTER_CONTROL_EVENT, onComputer)
      window.removeEventListener(OPEN_ROLE_PANE_EVENT, onRole)
    }
  }, [])

  const close = () => setOverlay(null)

  return (
    <>
      <SettingsSheet
        isOpen={overlay === 'settings'}
        onClose={close}
        initialSection={settingsSection}
        roleId={roleId}
      />
      <TeamsSheet isOpen={overlay === 'teams'} onClose={close} />
      <BlueprintsSheet isOpen={overlay === 'blueprints'} onClose={close} />
      <RolePaneSheet isOpen={overlay === 'role'} onClose={close} roleId={roleId} />
      <ComputerControlSheet isOpen={overlay === 'computer-control'} onClose={close} />
    </>
  )
}
