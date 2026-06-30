import re

with open('webui/frontend/src/pages/__tests__/BuilderPage.test.tsx', 'r') as f:
    content = f.read()

# Fix the syntax error in BuilderPage.test.tsx
new_content = re.sub(
    r"    render\(<BuilderPage \/>\);\n.*?  \}\);\n\n  it\('renders error state with assertive aria-live and alert role', \(\) => \{",
    "  it('renders error state with assertive aria-live and alert role', () => {",
    content,
    flags=re.DOTALL
)

with open('webui/frontend/src/pages/__tests__/BuilderPage.test.tsx', 'w') as f:
    f.write(new_content)
