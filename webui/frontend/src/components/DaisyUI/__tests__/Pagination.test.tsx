import { renderHook, act } from '@testing-library/react';
import { useInfiniteScroll } from '../Pagination';

describe('useInfiniteScroll', () => {
  it('should initialize with provided items and default states', () => {
    const initialItems = [1, 2, 3];
    const { result } = renderHook(() => useInfiniteScroll(initialItems));

    expect(result.current.items).toEqual(initialItems);
    expect(result.current.hasMore).toBe(true);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.isEmpty).toBe(false);
  });

  it('should correctly calculate isEmpty when no items are available', async () => {
    const { result } = renderHook(() => useInfiniteScroll([]));

    // Initially hasMore is true
    expect(result.current.isEmpty).toBe(false);

    // Mock fetch that returns empty
    const fetchFunction = vi.fn().mockResolvedValue([]);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(result.current.hasMore).toBe(false);
    expect(result.current.isEmpty).toBe(true);
  });

  it('should load more items and update state', async () => {
    const { result } = renderHook(() => useInfiniteScroll<number>([]));

    const fetchFunction = vi.fn().mockResolvedValue([1, 2, 3]);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(result.current.items).toEqual([1, 2, 3]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should handle errors during fetch and set error state', async () => {
    const { result } = renderHook(() => useInfiniteScroll([]));

    const testError = new Error('Fetch failed');
    const fetchFunction = vi.fn().mockRejectedValue(testError);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(result.current.error).toEqual(testError);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.items).toEqual([]); // unchanged
  });

  it('should reset to initial state', async () => {
    const initialItems = [1];
    const { result } = renderHook(() => useInfiniteScroll(initialItems));

    const fetchFunction = vi.fn().mockResolvedValue([2, 3]);

    await act(async () => {
      await result.current.loadMore(fetchFunction);
    });

    expect(result.current.items).toEqual([1, 2, 3]);

    act(() => {
      result.current.reset();
    });

    expect(result.current.items).toEqual(initialItems);
    expect(result.current.hasMore).toBe(true);
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });
});
