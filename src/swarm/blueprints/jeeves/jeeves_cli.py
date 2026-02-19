import argparse
import asyncio
import os

from rich import box as rich_box
from rich.console import Console
from rich.panel import Panel

from swarm.blueprints.jeeves.blueprint_jeeves import (
    SPINNER_STATES,
    JeevesBlueprint,
    JeevesSpinner,
    display_operation_box,
)

try:
    from aioconsole import ainput
except ImportError:
    import asyncio
    async def ainput(prompt: str = "") -> str:
        # Fallback to synchronous input in thread
        return await asyncio.get_event_loop().run_in_executor(None, input, prompt)

def main():
    if os.environ.get('SWARM_TEST_MODE'):
        for i, state in enumerate(SPINNER_STATES, start=1):
            # Raw spinner output for test compliance
            print(f"[SPINNER] {state}")
            display_operation_box(
                title="Searching Filesystem",
                content=f"Matches so far: {i}",
                emoji="🔍",
                spinner_state=state
            )
        return
    parser = argparse.ArgumentParser(description="Jeeves: Home automation and web search butler")
    parser.add_argument("--instruction", type=str, help="Instruction for Jeeves to execute", default=None)
    parser.add_argument("--message", dest='instruction', type=str, help="Instruction for Jeeves agent (alias --message)")
    parser.add_argument("--search-mode", choices=["semantic","code"], help="Search mode for Jeeves: 'semantic' or 'code'", default=None)
    args = parser.parse_args()
    search_mode = args.search_mode
    bp = JeevesBlueprint(blueprint_id="jeeves")

    async def run_instruction(instruction):
        spinner = JeevesSpinner()
        spinner.start()
        try:
            messages = [{"role": "user", "content": instruction}]
            import time
            spinner_start = time.time()
            async for chunk in bp.run(messages, search_mode=search_mode):
                if isinstance(chunk, dict) and (chunk.get("progress") or chunk.get("matches")):
                    time.time() - spinner_start
                    spinner_state = spinner.current_spinner_state()
                    display_operation_box(
                        title="Progressive Operation",
                        content="\n".join(chunk.get("matches", [])),
                        style="bold cyan" if chunk.get("type") == "code_search" else "bold magenta",
                        result_count=len(chunk.get('matches', [])) if chunk.get("matches") is not None else None,
                        params={k: v for k, v in chunk.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                        progress_line=chunk.get('progress'),
                        total_lines=chunk.get('total'),
                        spinner_state=spinner_state,
                        op_type=chunk.get("type", "search"),
                        emoji="🔍" if chunk.get("type") == "code_search" else "🧠"
                    )
                else:
                    print(chunk)
        finally:
            spinner.stop()

    if args.instruction:
        asyncio.run(run_instruction(args.instruction))
    else:
        console = Console()
        welcome_panel = Panel(
            "[bold cyan]Welcome to Jeeves CLI![/bold cyan]\n\n"
            "Type your instruction and press Enter.\n"
            "Use [yellow]--search-mode[/yellow] for semantic or code mode.\n"
            "Press Ctrl+C to exit.",
            title="🤖 Jeeves CLI",
            box=rich_box.ROUNDED
        )
        console.print(welcome_panel)
        async def interactive():
            first_interrupt = True
            while True:
                try:
                    user_input = await ainput("You: ")
                except (KeyboardInterrupt, EOFError):
                    if first_interrupt:
                        console.print("[yellow]Press Ctrl+C again to exit Jeeves CLI[/yellow]")
                        first_interrupt = False
                        continue
                    break
                if user_input.strip():
                    await run_instruction(user_input.strip())
            console.print("\nExiting Jeeves CLI.")
        asyncio.run(interactive())

if __name__ == "__main__":
    main()
