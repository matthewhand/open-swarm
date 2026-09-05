import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SkillPopup } from '../SkillPopup'

describe('SkillPopup (REQ-212)', () => {
  it('shows name, description, source path, and body preview', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          name: 'conventional-commit',
          id: 'conventional-commit',
          description: 'Write a conventional commit.',
          path: 'skills/conventional-commit/SKILL.md',
          assets: [],
          instructions: 'Use type(scope): summary.',
          found: true,
        }),
      }),
    )
    const onClose = vi.fn()
    render(<SkillPopup name="conventional-commit" open onClose={onClose} />)
    expect(await screen.findByTestId('skill-popup-name')).toHaveTextContent('conventional-commit')
    expect(screen.getByTestId('skill-popup-source')).toHaveTextContent(
      'skills/conventional-commit/SKILL.md',
    )
    expect(screen.getByTestId('skill-popup-instructions')).toHaveTextContent('type(scope)')
    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalled()
    vi.unstubAllGlobals()
  })

  it('shows an honest error when the skill cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({
          name: 'nope',
          found: false,
          error: "Skill 'nope' not found. Add a SKILL.md under skills/ (see docs/SKILLS.md).",
        }),
      }),
    )
    render(<SkillPopup name="nope" open onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByTestId('skill-popup-error')).toHaveTextContent('not found')
    })
    expect(screen.getByTestId('skill-popup-visibility')).toHaveTextContent('Missing')
    vi.unstubAllGlobals()
  })
})
