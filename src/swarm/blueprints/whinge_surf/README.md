# Whinge Surf Blueprint

**Whinge Surf** is a blueprint for Open Swarm that lets you launch background subprocesses, check on their status, and view their console output—perfect for monitoring long-running or noisy tasks without blocking your main workflow.

## Features
- Launch subprocesses in the background
- Check if a subprocess has finished
- View live or completed console output for any subprocess

## Why is it special?
Whinge Surf is your "background task butler"—it lets you surf the waves of whinging (output) from your processes, without getting bogged down. Great for CI jobs, long scripts, or anything you want to keep an eye on from afar.

## Example Usage
```python
from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint
ws = WhingeSurfBlueprint()
pid = ws.run_subprocess_in_background(["python", "my_script.py"])
status = ws.check_subprocess_status(pid)
output = ws.get_subprocess_output(pid)
```

---
