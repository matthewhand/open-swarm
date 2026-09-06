import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AgentWorkspaceBinding from '../AgentWorkspaceBinding'
import {
  COMING_SOON_LABEL,
  FOLDER_EMPTY_STATE,
  GITHUB_REPO_EMPTY_STATE,
  WORKSPACE_SECTION_TITLE,
  emptyWorkspaceFields,
} from '../../lib/agentWorkspace'

describe('AgentWorkspaceBinding (REQ-166 Phase 0)', () => {
  it('shows CLI Folder with empty-state and path hints, plus coming-soon repo/workspaces', () => {
    const onChange = vi.fn()
    render(
      <AgentWorkspaceBinding kind="cli" value={emptyWorkspaceFields()} onChange={onChange} />,
    )

    expect(screen.getByTestId('agent-workspace-binding')).toHaveAttribute(
      'data-workspace-kind',
      'cli',
    )
    expect(screen.getByText(WORKSPACE_SECTION_TITLE)).toBeInTheDocument()
    expect(screen.getByTestId('input-cli-folder')).toBeEnabled()
    expect(screen.getByTestId('workspace-folder-hint')).toHaveTextContent(/Working directory/i)
    expect(screen.getByTestId('workspace-folder-empty')).toHaveTextContent(FOLDER_EMPTY_STATE)
    expect(screen.getByTestId('input-github-repo')).toBeInTheDocument()
    expect(screen.getByTestId('workspace-repo-empty')).toHaveTextContent(GITHUB_REPO_EMPTY_STATE)
    expect(screen.getByTestId('toggle-workspaces')).toBeDisabled()
    expect(screen.getAllByText(COMING_SOON_LABEL).length).toBeGreaterThanOrEqual(2)
  })

  it('reports invalid folder and repo format chrome', () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <AgentWorkspaceBinding kind="cli" value={emptyWorkspaceFields()} onChange={onChange} />,
    )

    fireEvent.change(screen.getByTestId('input-cli-folder'), {
      target: { value: '/bad/*/path' },
    })
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ folder: '/bad/*/path' }),
    )

    rerender(
      <AgentWorkspaceBinding
        kind="cli"
        value={{ folder: '/bad/*/path', githubRepo: 'not a repo', workspacesEnabled: false }}
        onChange={onChange}
        folderError="Please enter a valid directory path (e.g. /path/to/dir or ./dir)"
      />,
    )
    expect(screen.getByTestId('folder-error')).toBeInTheDocument()
    expect(screen.getByTestId('repo-error')).toBeInTheDocument()
  })

  it('stubs API and Remote kinds as coming soon without Folder controls', () => {
    const { rerender } = render(
      <AgentWorkspaceBinding kind="api" value={emptyWorkspaceFields()} onChange={vi.fn()} />,
    )
    expect(screen.getByTestId('workspace-kind-stub')).toBeInTheDocument()
    expect(screen.queryByTestId('input-cli-folder')).not.toBeInTheDocument()
    expect(screen.getByText(COMING_SOON_LABEL)).toBeInTheDocument()

    rerender(
      <AgentWorkspaceBinding kind="remote" value={emptyWorkspaceFields()} onChange={vi.fn()} />,
    )
    expect(screen.getByTestId('agent-workspace-binding')).toHaveAttribute(
      'data-workspace-kind',
      'remote',
    )
    expect(screen.getByTestId('workspace-kind-stub')).toBeInTheDocument()
  })
})
