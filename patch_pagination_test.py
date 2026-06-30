import re

with open('webui/frontend/src/components/DaisyUI/__tests__/Pagination.test.tsx', 'r') as f:
    content = f.read()

# Fix the act wrapping in should correctly calculate isEmpty when no items are available
new_test = """  it('should correctly calculate isEmpty when no items are available', async () => {
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
  });"""

content = re.sub(
    r"  it\('should correctly calculate isEmpty when no items are available', \(\) => \{\n[\s\S]*?\}\);",
    new_test,
    content
)

with open('webui/frontend/src/components/DaisyUI/__tests__/Pagination.test.tsx', 'w') as f:
    f.write(content)

print("Pagination.test.tsx patched")
