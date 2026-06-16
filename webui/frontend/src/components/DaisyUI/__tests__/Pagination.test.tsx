import { renderHook, act } from '@testing-library/react';
import { useInfiniteScroll } from '../Pagination';

describe('useInfiniteScroll Hook', () => {
  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useInfiniteScroll());
    expect(result.current.items).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.hasMore).toBe(true);
  });

  it('should correctly fetch and append items', async () => {
    const { result } = renderHook(() => useInfiniteScroll<number>());

    let callCount = 0;
    const mockFetch = async () => {
      callCount++;
      return callCount === 1 ? [1, 2] : [3, 4];
    };

    await act(async () => {
      await result.current.loadMore(mockFetch);
    });

    expect(result.current.items).toEqual([1, 2]);
    expect(result.current.isLoading).toBe(false);

    await act(async () => {
      await result.current.loadMore(mockFetch);
    });

    expect(result.current.items).toEqual([1, 2, 3, 4]);
  });

  it('should correctly handle empty fetch responses to stop loading more', async () => {
    const { result } = renderHook(() => useInfiniteScroll<number>());

    const mockFetchEmpty = async () => [];

    await act(async () => {
      await result.current.loadMore(mockFetchEmpty);
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.hasMore).toBe(false);
  });

  it('should handle errors gracefully by setting isError and error object', async () => {
    const { result } = renderHook(() => useInfiniteScroll<number>());

    const mockErrorFetch = async () => {
      throw new Error('Network error');
    };

    await act(async () => {
      await result.current.loadMore(mockErrorFetch);
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Network error');
    expect(result.current.isLoading).toBe(false);
  });

  it('should reset state correctly', () => {
    const { result } = renderHook(() => useInfiniteScroll<number>([1]));

    act(() => {
      result.current.setItems([1, 2, 3]);
    });
    expect(result.current.items).toEqual([1, 2, 3]);

    act(() => {
      result.current.reset();
    });

    expect(result.current.items).toEqual([1]);
    expect(result.current.hasMore).toBe(true);
    expect(result.current.isError).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
