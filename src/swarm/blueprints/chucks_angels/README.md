# chucks_angels

Chuck's Angels coordinates "angelic" tasks in a humorous, Chuck Norris style.

## Features

- Basic BlueprintBase implementation.
- Responds to user messages with fun "mission accomplished" style output.
- Metadata: name "Chuck's Angels", abbreviation "angels", emoji 😇.

## Environment Variables

None specific (uses standard LLM config).

## Usage

```bash
swarm-cli install chucks_angels
swarm-cli launch chucks_angels --message "Help with my task"
```

See `blueprint_chucks_angels.py` and its test_basic.py for current behavior (simple echo + roundhouse kick flavor).
