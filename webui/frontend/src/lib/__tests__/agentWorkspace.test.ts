import { afterEach, describe, expect, it } from 'vitest'
import { AGENT_EDITS_KEY, saveAgentEdit } from '../agentEdits'
import {
  FOLDER_FORMAT_ERROR,
  GITHUB_REPO_FORMAT_ERROR,
  emptyWorkspaceFields,
  isValidFolderPath,
  isValidGithubRepo,
  loadAgentWorkspace,
  saveAgentWorkspace,
} from '../agentWorkspace'

describe('agentWorkspace (REQ-166 Phase 0)', () => {
  afterEach(() => {
    localStorage.removeItem(AGENT_EDITS_KEY)
  })

  it('starts empty and persists folder + repo without enabling workspaces', () => {
    expect(loadAgentWorkspace('cli_agent')).toEqual(emptyWorkspaceFields())
    const saved = saveAgentWorkspace('cli_agent', {
      folder: '  /home/dev/tool  ',
      githubRepo: '  acme/app  ',
      workspacesEnabled: true,
    })
    expect(saved).toEqual({
      folder: '/home/dev/tool',
      githubRepo: 'acme/app',
      workspacesEnabled: true,
    })
    expect(loadAgentWorkspace('cli_agent')).toEqual(saved)
  })

  it('clears workspaces when repo is blank or invalid', () => {
    saveAgentEdit('cli_agent', { githubRepo: 'acme/app', workspacesEnabled: true })
    expect(saveAgentWorkspace('cli_agent', { githubRepo: '' }).workspacesEnabled).toBe(false)
    saveAgentEdit('cli_agent', { githubRepo: 'acme/app', workspacesEnabled: true })
    expect(saveAgentWorkspace('cli_agent', { githubRepo: 'not a repo' }).workspacesEnabled).toBe(false)
  })

  it('validates folder path format chrome', () => {
    expect(isValidFolderPath('')).toBe(true)
    expect(isValidFolderPath('/home/dev/tool')).toBe(true)
    expect(isValidFolderPath('./project')).toBe(true)
    expect(isValidFolderPath('/invalid/*/path')).toBe(false)
    expect(FOLDER_FORMAT_ERROR).toMatch(/valid directory path/i)
  })

  it('validates GitHub repo format chrome', () => {
    expect(isValidGithubRepo('')).toBe(true)
    expect(isValidGithubRepo('acme/app')).toBe(true)
    expect(isValidGithubRepo('https://github.com/acme/app')).toBe(true)
    expect(isValidGithubRepo('https://github.com/acme/app.git')).toBe(true)
    expect(isValidGithubRepo('not a repo')).toBe(false)
    expect(isValidGithubRepo('https://example.com/acme/app')).toBe(false)
    expect(GITHUB_REPO_FORMAT_ERROR).toMatch(/owner\/repo/i)
  })
})
