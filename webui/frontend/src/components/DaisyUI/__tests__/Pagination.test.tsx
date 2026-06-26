import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useInfiniteScroll } from '../Pagination';

describe('useInfiniteScroll Hook', () => {
  it('should initialize with correct default state and types', () => {
    const { result } = renderHook(() => useInfiniteScroll<string>(['item1']));

    expect(result.current.items).toEqual(['item1']);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.isEmpty).toBe(false);
    expect(result.current.hasMore).toBe(true);
  });

  it('should update state to isEmpty when items are empty after loading', async () => {
    const { result } = renderHook(() => useInfiniteScroll<string>([]));

    const mockFetch = vi.fn().mockResolvedValue([]);

    expect(result.current.isEmpty).toBe(true); // initially empty

    await act(async () => {
      await result.current.loadMore(mockFetch);
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.hasMore).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isEmpty).toBe(true);
  });

  it('should populate error state when load fails', async () => {
    const { result } = renderHook(() => useInfiniteScroll<string>([]));

    const mockFetch = vi.fn().mockRejectedValue(new Error('Network failure'));

    await act(async () => {
      await result.current.loadMore(mockFetch);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Network failure');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isEmpty).toBe(false); // When there's an error, it shouldn't show as cleanly 'empty' to the UI state machine
  });
});
