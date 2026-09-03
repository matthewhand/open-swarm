import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import AvatarStack from '../AvatarStack'

describe('AvatarStack', () => {
  it('renders 3 faces + remainder and staggers animation-delay from started_at', () => {
    const { container } = render(
      <AvatarStack
        faces={[
          { id: 'c', name: 'C', startedAt: 1800 },
          { id: 'b', name: 'B', startedAt: 1400 },
          { id: 'a', name: 'A', startedAt: 1000 },
        ]}
        remainder={2}
        animate
      />,
    )
    const stack = container.querySelector('[data-avatar-stack="true"]')
    expect(stack).toBeTruthy()
    expect(stack).toHaveAttribute('data-stack-count', '3')
    expect(stack).toHaveAttribute('data-remainder', '2')
    expect(container.querySelector('[data-remainder-count="2"]')).toHaveTextContent('+2')

    const faces = [...container.querySelectorAll<HTMLElement>('.os-avatar-stack__face')]
    expect(faces).toHaveLength(3)
    expect(faces.every((face) => face.classList.contains('os-avatar-stack__face--working'))).toBe(
      true,
    )
    expect(faces.map((face) => face.style.animationDelay)).toEqual(['800ms', '400ms', '0ms'])
  })

  it('renders a single face without stack treatment', () => {
    const { container } = render(
      <AvatarStack faces={[{ id: 'hermes', name: 'Hermes', startedAt: 1 }]} remainder={0} />,
    )
    expect(container.querySelector('[data-avatar-stack="false"]')).toBeTruthy()
    expect(container.querySelectorAll('.os-avatar-stack__face')).toHaveLength(1)
    expect(container.querySelector('[data-remainder-count]')).toBeNull()
  })
})
