import re

with open('webui/frontend/src/components/DaisyUI/Pagination.tsx', 'r') as f:
    content = f.read()

# Replace useInfiniteScroll definition
new_hook = """export const useInfiniteScroll = <T,>(
  initialItems: T[] = [],
  itemsPerPage: number = 10
) => {
  const [items, setItems] = useState<T[]>(initialItems);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [page, setPage] = useState(1);

  const isEmpty = items.length === 0 && !hasMore && !isLoading && !error;

  const loadMore = async (fetchFunction: (page: number, itemsPerPage: number) => Promise<T[]>) => {
    if (isLoading || !hasMore) return;

    setIsLoading(true);
    setError(null);
    try {
      const newItems = await fetchFunction(page + 1, itemsPerPage);

      if (newItems.length === 0) {
        setHasMore(false);
      } else {
        setItems(prev => [...prev, ...newItems]);
        setPage(prev => prev + 1);
      }
    } catch (err) {
      console.error('Error loading more items:', err);
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setItems(initialItems);
    setHasMore(true);
    setError(null);
    setPage(1);
  };

  return {
    items,
    hasMore,
    isLoading,
    error,
    isEmpty,
    loadMore,
    reset,
    setItems,
  };
};"""

content = re.sub(
    r'export const useInfiniteScroll = \([\s\S]*?\}\s*;\s*\}\s*;\s*\n\s*return \{\s*items,\s*hasMore,\s*isLoading,\s*loadMore,\s*reset,\s*setItems,\s*\};\s*\};',
    new_hook,
    content
)

with open('webui/frontend/src/components/DaisyUI/Pagination.tsx', 'w') as f:
    f.write(content)

print("Pagination.tsx patched")
