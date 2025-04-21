#!/usr/bin/env python3
"""
Blueprint UX/Spinner Demo Mode
Animates all standardized spinner states and ANSI/emoji boxes for visual verification.
"""
from time import sleep
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.style import Style
import itertools

SPINNER_FRAMES = [
    "Generating.",
    "Generating..",
    "Generating...",
    "Running..."
]
SLOW_FRAME = "Generating... Taking longer than expected"

console = Console()
def spinner_demo():
    console.print("\n[bold green]Spinner Demo: Standard Swarm UX[/bold green]")
    for i in range(2):
        for frame in SPINNER_FRAMES:
            console.print(Text(frame, style=Style(color="cyan", bold=True)), end="\r", soft_wrap=True, highlight=False)
            sleep(0.3)
    console.print(Text(SLOW_FRAME, style=Style(color="yellow", bold=True)), end="\r", soft_wrap=True, highlight=False)
    sleep(1)
    console.print(" " * 40, end="\r")
    console.print("[bold green]Spinner demo complete!\n[/bold green]")

def ansi_box_demo():
    console.print("[bold blue]ANSI/Emoji Box Demo[/bold blue]")
    panel = Panel("Searched filesystem\nResults: 42 files\nParams: *.py, recursive\nLine: 1-100", title="[bold yellow]Search Summary[/bold yellow]", border_style="yellow", expand=False)
    console.print(panel)
    panel2 = Panel("Analyzed codebase\nResults: 12 matches\nParams: semantic, fuzzy\nLine: 1-200", title="[bold magenta]Analysis Summary[/bold magenta]", border_style="magenta", expand=False)
    console.print(panel2)
    console.print("[bold green]ANSI/Emoji box demo complete!\n[/bold green]")

def main():
    spinner_demo()
    ansi_box_demo()

if __name__ == "__main__":
    main()
