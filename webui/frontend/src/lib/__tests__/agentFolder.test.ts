import { afterEach, describe, expect, it } from 'vitest'
import { AGENT_EDITS_KEY, saveAgentEdit } from '../agentEdits'
import {
  chatFolderParams,
  folderRequestValue,
  isValidFolderPath,
  loadAgentFolder,
} from '../agentFolder'

describe('agentFolder (REQ-167)', () => {
  afterEach(() => {
    localStorage.removeItem(AGENT_EDITS_KEY)
  })

  it('persists folder on the agent edit record', () => {
    saveAgentEdit('cli_agent', { folder: '  /home/dev/tool  ' })
    expect(loadAgentFolder('cli_agent')).toBe('/home/dev/tool')
    expect(folderRequestValue('cli_agent')).toBe('/home/dev/tool')
    expect(chatFolderParams('cli_agent')).toEqual({ folder: '/home/dev/tool' })
  })

  it('omits folder from session/chat params when unset', () => {
    expect(loadAgentFolder('cli_agent')).toBe('')
    expect(folderRequestValue('cli_agent')).toBeUndefined()
    expect(chatFolderParams('cli_agent')).toBeUndefined()
  })

  it('rejects invalid path format', () => {
    expect(isValidFolderPath('')).toBe(true)
    expect(isValidFolderPath('/home/dev/tool')).toBe(true)
    expect(isValidFolderPath('./project')).toBe(true)
    expect(isValidFolderPath('/invalid/*/path')).toBe(false)
  })
})
