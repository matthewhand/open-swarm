import re

with open('webui/frontend/src/pages/__tests__/BuilderPage.test.tsx', 'r') as f:
    content = f.read()

new_test = """  it('renders loading state with polite aria-live and aria-busy', () => {
    (useQuery as any).mockImplementation(({ queryKey }: any) => {
      if (queryKey[0] === 'blueprints') {
        return { isPending: true, isError: false, data: undefined };
      }
      return { isPending: false, isError: false, data: undefined };
    });

    const { container } = render(<BuilderPage />);
    // Querying for aria-busy="true" instead of using parentElement to avoid no-node-access
    const busyContainer = container.querySelector('[aria-busy="true"]');

    expect(busyContainer).toHaveAttribute('aria-live', 'polite');
    expect(busyContainer).toHaveAttribute('aria-busy', 'true');
  });"""

content = re.sub(
    r"  it\('renders loading state with polite aria-live and aria-busy', \(\) => \{\n[\s\S]*?  \}\);",
    new_test,
    content
)

with open('webui/frontend/src/pages/__tests__/BuilderPage.test.tsx', 'w') as f:
    f.write(content)
