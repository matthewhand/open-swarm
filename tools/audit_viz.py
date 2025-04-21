#!/usr/bin/env python3
"""
Audit Trail Visualization Tool for Open Swarm
Reads .jsonl audit logs and prints a timeline of agent/tool actions, errors, and reflections.
"""
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

if len(sys.argv) < 2:
    print("Usage: audit_viz.py <audit_log.jsonl>")
    sys.exit(1)

log_path = Path(sys.argv[1])
if not log_path.exists():
    print(f"File not found: {log_path}")
    sys.exit(1)

console = Console()
table = Table(title="Swarm Audit Trail Timeline")
table.add_column("Time", style="dim")
table.add_column("Event Type", style="cyan")
table.add_column("Details", style="white")

with log_path.open() as f:
    for line in f:
        try:
            entry = json.loads(line)
            time = entry.get("time", "?")
            event = entry.get("event", entry.get("type", "?"))
            details = str(entry.get("details", entry))[:80]
            table.add_row(time, event, details)
        except Exception as e:
            table.add_row("?", "ERROR", str(e))

console.print(table)
