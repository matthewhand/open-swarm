import { afterEach, describe, expect, it } from 'vitest'
import {
  RAIL_ORDER_STORAGE_KEY,
  applyRailOrder,
  bumpRailIdToTop,
  loadRailOrder,
  mergeRailOrder,
  moveRailId,
  saveRailOrder,
} from '../railOrder'

describe('railOrder persistence', () => {
  afterEach(() => {
    localStorage.removeItem(RAIL_ORDER_STORAGE_KEY)
  })

  it('starts empty, persists a drag order, and reloads it', () => {
    expect(loadRailOrder()).toEqual([])
    expect(saveRailOrder(['stewie', 'support', 'codey'])).toEqual([
      'stewie',
      'support',
      'codey',
    ])
    expect(JSON.parse(localStorage.getItem(RAIL_ORDER_STORAGE_KEY) || '[]')).toEqual([
      'stewie',
      'support',
      'codey',
    ])
    expect(loadRailOrder()).toEqual(['stewie', 'support', 'codey'])
  })

  it('ignores corrupt storage and empty ids', () => {
    localStorage.setItem(RAIL_ORDER_STORAGE_KEY, '{not-json')
    expect(loadRailOrder()).toEqual([])
    localStorage.setItem(RAIL_ORDER_STORAGE_KEY, JSON.stringify([1, '', 'ok', 'ok']))
    expect(loadRailOrder()).toEqual(['ok'])
  })

  it('applies stored order and appends new catalog rows', () => {
    const items = [{ id: 'support' }, { id: 'codey' }, { id: 'stewie' }]
    expect(applyRailOrder(items, ['stewie', 'codey']).map((item) => item.id)).toEqual([
      'stewie',
      'codey',
      'support',
    ])
  })

  it('moves a row before another and bumps a completed id to index 0', () => {
    const start = ['support', 'codey', 'stewie']
    expect(moveRailId(start, 'stewie', 'support')).toEqual(['stewie', 'support', 'codey'])
    expect(moveRailId(start, 'codey', 'codey')).toEqual(start)
    expect(bumpRailIdToTop(start, 'stewie')).toEqual(['stewie', 'support', 'codey'])
    expect(mergeRailOrder(['stewie'], ['support', 'codey', 'stewie'])).toEqual([
      'stewie',
      'support',
      'codey',
    ])
  })
})
