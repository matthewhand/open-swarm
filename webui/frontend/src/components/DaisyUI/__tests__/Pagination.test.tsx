import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useInfiniteScroll } from '../Pagination';

describe('useInfiniteScroll', () => {
  it('should initialize with generic items array correctly', () => {
    // Testing generic typing T parameter explicitly
    interface User { id: number; name: string }
    const initialData: User[] = [{ id: 1, name: 'Alice' }];

    const { result } = renderHook(() => useInfiniteScroll<User>(initialData, 10));

    expect(result.current.items).toEqual(initialData);
    expect(result.current.items[0].name).toBe('Alice');
    expect(result.current.hasMore).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it('should load more generic items and update state', async () => {
    const { result } = renderHook(() => useInfiniteScroll<number>([1, 2], 2));

    const fetchFunction = vi.fn().mockResolvedValue([3, 4]);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(fetchFunction).toHaveBeenCalledWith(2, 2);
    expect(result.current.items).toEqual([1, 2, 3, 4]);
  });

  it('should set hasMore to false when no items are returned', async () => {
    const { result } = renderHook(() => useInfiniteScroll<string>(['a'], 5));

    const fetchFunction = vi.fn().mockResolvedValue([]);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(result.current.hasMore).toBe(false);
    expect(result.current.items).toEqual(['a']); // items remain the same
  });
});
