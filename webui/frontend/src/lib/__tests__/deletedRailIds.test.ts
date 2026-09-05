import { afterEach, describe, expect, it } from 'vitest'
import {
  DELETED_RAIL_IDS_KEY,
  isRailIdDeleted,
  loadDeletedRailIds,
  markRailIdDeleted,
} from '../deletedRailIds'

describe('deletedRailIds (REQ-82)', () => {
  afterEach(() => {
    localStorage.removeItem(DELETED_RAIL_IDS_KEY)
  })

  it('persists deleted ids and reports membership', () => {
    expect(loadDeletedRailIds()).toEqual([])
    const next = markRailIdDeleted('codey')
    expect(next).toEqual(['codey'])
    expect(isRailIdDeleted('codey')).toBe(true)
    expect(isRailIdDeleted('stewie')).toBe(false)
    expect(JSON.parse(localStorage.getItem(DELETED_RAIL_IDS_KEY) || '[]')).toEqual(['codey'])
  })
})
