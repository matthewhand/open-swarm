import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SkillChip } from '../SkillChip'

describe('SkillChip (REQ-212)', () => {
  it('renders a clickable chip for a loaded skill, not the bare path', () => {
    const onClick = vi.fn()
    render(
      <SkillChip
        name="conventional-commit"
        raw="skills/conventional-commit/SKILL.md"
        skill={{
          name: 'conventional-commit',
          description: 'Write a conventional commit.',
          path: 'skills/conventional-commit/SKILL.md',
          assets: [],
        }}
        onClick={onClick}
      />,
    )
    const chip = screen.getByTestId('skill-chip')
    expect(chip).toHaveTextContent('conventional-commit')
    expect(chip).not.toHaveTextContent('skills/conventional-commit/SKILL.md')
    expect(chip).toHaveAttribute('data-skill-missing', 'false')
    fireEvent.click(chip)
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('fails honestly when the skill is missing', () => {
    render(<SkillChip name="nope-not-real" missing />)
    const chip = screen.getByTestId('skill-chip')
    expect(chip).toHaveAttribute('data-skill-missing', 'true')
    expect(chip).toHaveTextContent('Missing')
  })
})
