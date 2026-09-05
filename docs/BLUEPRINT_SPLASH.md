# Blueprint Splash Abstraction

## Purpose
The splash is a visually engaging, branded introduction message shown when a blueprint is started in an interactive terminal (CLI) environment. Blueprints are CLI/API only — they do not ship a webpage; the Grok-like WebUI is product chrome. The splash is CLI chrome, not a WebUI. It typically includes the blueprint’s name, purpose, and features, styled with ANSI colors, Unicode boxes, and emoji for clarity and impact.

## Key Principles
- **Single Splash:** Each blueprint defines only one splash, generated from its metadata (title, description, etc.), and styled for CLI use.
- **Display Rules:**
  - **Show splash only in interactive CLI mode.**
  - **Do NOT show splash in non-interactive CLI mode** (e.g., when running with `--message`, `--instruction`, or piping input).
  - **Never show splash in API mode**—the API should only expose metadata.
- **Source of Truth:** All splash content is derived from the blueprint’s metadata. The CLI may decorate this with ANSI/emoji, but the info itself is canonical and structured.

## Implementation Pattern
- Each blueprint defines its metadata (title, description, etc.).
- There is a single `get_splash()` method (or property) that returns the decorated splash (using ANSI/emoji/boxes).
- The CLI entrypoint is responsible for:
  - Detecting if it’s running interactively.
  - Printing the splash only if interactive.

### Example Implementation
```python
# In blueprint base or per-blueprint
def get_splash(self):
    from swarm.core.output_utils import ansi_box
    return ansi_box(
        self.metadata['title'],
        self.metadata['description'],
        color='96',
        emoji='🤖',
    )

# In CLI entrypoint:
import sys

def is_interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()

if __name__ == "__main__":
    if is_interactive():
        print(bp.get_splash())
    main()
```

## Summary Table
| Mode                | Splash Shown? | Output Format      |
|---------------------|--------------|--------------------|
| CLI Interactive     | Yes          | ANSI/emoji/box     |
| CLI Non-Interactive | No           | None               |
| API                 | No           | None (metadata only)|

## Rationale
This approach keeps things simple, avoids duplication, and ensures the splash never appears in non-interactive or API contexts. All user-facing and programmatic interfaces have clear, predictable behavior.

---

**Reference this file in blueprint and CLI documentation to ensure consistent behavior across all blueprints.**
