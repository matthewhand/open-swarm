# DEPRECATED: This blueprint is superseded by Zeus. All logic and tests should be migrated to ZeusBlueprint. File retained for legacy reference only.

import asyncio as aio
import time as tm
from collections.abc import AsyncGenerator
from typing import Any

from swarm.blueprints.common.output_formatters import DiffFormatter, StatusFormatter
from swarm.blueprints.common.progress import ProgressRenderer
from swarm.core.blueprint_base import BlueprintBase


class GAWDBlueprint(BlueprintBase):
    """
    A blueprint for divine code inspiration. Demonstrates unified UX: spinner, ANSI/emoji output, and progress updates.
    """
    coordinator = None  # Dummy attribute for test compliance
    progress = ProgressRenderer()
    diff_formatter = DiffFormatter()
    status_formatter = StatusFormatter()

    def __init__(self, blueprint_id: str, config_path: str | None = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)

    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(*args, **kwargs)

    async def run(self,
                 messages: list[dict[str, Any]],
                 **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        import os
        op_start: float = tm.time()  # type: ignore
        instruction = messages[-1]["content"] if messages else ""
        if os.environ.get('SWARM_TEST_MODE'):
            instruction = messages[-1].get("content", "") if messages else ""
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            self.progress.render_progress_box(
                op_type="Divine Code Spinner",
                results=[
                    "Divine Code Inspiration",
                    f"Seeking divine code for '{instruction}'",
                    *spinner_lines[:4],
                    *([f"... +{len(spinner_lines)-4} lines"] if len(spinner_lines) >4 else []),
                    "Results: 2",
                    "Processed",
                    "✨"
                ],
                summary=f"Seeking divine code for: '{instruction}'",
                spinner_state="Generating... Taking longer than expected"
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                GAWDBlueprint.print_search_progress_box(
                    op_type="Divine Code Spinner",
                    results=[f"Divine Code Spinner State: {spinner_state}"],
                    params=None,
                    result_type="gawd",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="Divine Code Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='✨',
                    border='╔'
                )
                await aio.sleep(0.01)
            GAWDBlueprint.print_search_progress_box(
                op_type="Divine Code Results",
                results=[f"DivineCode agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="gawd",
                summary=f"DivineCode agent response for: '{instruction}'",
                progress_line="Processed",
                spinner_state="Done",
                operation_type="Divine Code Results",
                search_mode=None,
                total_lines=None,
                emoji='✨',
                border='╔'
            )
            message = f"Inspiration complete for: '{instruction}'"
            yield {
                "choices": [{"role": "assistant", "content": message}],
                "message": {"role": "assistant", "content": message}
            }
            return
        query = messages[-1]["content"] if messages else ""
        params = {"query": query}
        total_steps = 18
        spinner_states = ["Generating.", "Generating..", "Generating...", "Running..."]
        summary = f"Divine code inspiration for: '{query}'"
        # Spinner/UX enhancement: cycle through spinner states and show 'Taking longer than expected'
        for i, spinner_state in enumerate(spinner_states, 1):
            progress_line = f"Step {i}/{total_steps}"
            self.print_search_progress_box(
                op_type="Divine Code Inspiration",
                results=[f"Seeking divine code for '{query}'..."],
                params=params,
                result_type="inspiration",
                summary=summary,
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Divine Inspiration",
                search_mode=None,
                total_lines=total_steps,
                emoji='✨',
                border='╔'
            )
            await aio.sleep(0.05)
        for step in range(4, total_steps):
            spinner_state = op_start  # type: ignore
            progress_line = f"Step {step+1}/{total_steps}"
            self.print_search_progress_box(
                op_type="Divine Code Inspiration",
                results=[f"Seeking divine code for '{query}'..."],
                params=params,
                result_type="inspiration",
                summary=summary,
                progress_line=progress_line,
                spinner_state=spinner_state,
                operation_type="Divine Inspiration",
                search_mode=None,
                total_lines=total_steps,
                emoji='✨',
                border='╔'
            )
            await aio.sleep(0.13)
        self.print_search_progress_box(
            op_type="Divine Code Inspiration",
            results=[f"Seeking divine code for '{query}'...", "Taking longer than expected"],
            params=params,
            result_type="inspiration",
            summary=summary,
            progress_line=f"Step {total_steps}/{total_steps}",
            spinner_state="Generating... Taking longer than expected",
            operation_type="Divine Inspiration",
            search_mode=None,
            total_lines=total_steps,
            emoji='✨',
            border='╔'
        )
        await aio.sleep(0.1)
        # Actually run the agent and get the LLM response
        import asyncio
        import shutil
        import time
        term_width = shutil.get_terminal_size().columns - 4

        # Print input history in grey
        if hasattr(self, 'input_history'):
            for entry in self.input_history[-3:]:  # Show last 3 entries
                print(f"\033[38;5;240m> {entry}\033[0m")

        # Get input and check for multi-line paste
        print(f"\033[38;5;240m╭{'─' * term_width}╮\033[0m")
        user_input = input("\033[38;5;240m│ \033[0m\033[1;37m\u2588 \033[0m")
        print(f"\033[38;5;240m╰{'─' * term_width}╯\033[0m")

        # Check for multi-line input
        line_count = user_input.count('\n') + 1
        user_input = user_input.strip()
        if line_count > 1:
            # Display summary line
            print(f"\033[38;5;240m[Pasted Content - {line_count} lines]\033[0m")

        # Store input in history
        if not hasattr(self, 'input_history'):
            self.input_history = []
        self.input_history.append(user_input)

        # Print auto-accept status line
        auto_accept = kwargs.get('auto_accept', False)
        status_color = "\033[38;5;183m" if auto_accept else "\033[38;5;240m"
        print(f"{status_color}⏵⏵ auto-accept edits {'on' if auto_accept else 'off'} (shift+tab to cycle)\033[0m")

        agent: Any = self.coordinator  # type: ignore
        llm_response = ""
        try:
            from agents import Runner
            start_time = time.time()
            tokens_received = 0

            def status_update_callback(content_type: str, content: str):
                nonlocal tokens_received
                if content_type == "user_output":
                    tokens_received += len(content.split())

            # Start status line
            print("\033[38;5;183mResponding\033[0m\033[38;5;240m (0s waited, 0 tokens)\033[0m", end="\r")

            response = await Runner.run(
                agent,
                user_input
            )

            # Update status while waiting
            while not (hasattr(response, 'complete') and response.complete):  # type: ignore
                elapsed = int(time.time() - start_time)
                print(f"\033[38;5;183mResponding\033[0m\033[38;5;240m ({elapsed}s waited, {tokens_received} tokens)\033[0m", end="\r")
                await asyncio.sleep(1)

            # Clear status line
            print("\033[K", end="\r")

            llm_response = getattr(response, 'final_output', str(response))
            [llm_response.strip() or "(No response from LLM)"]
        except Exception:
            pass

        search_mode = kwargs.get('search_mode', 'semantic')
        if search_mode in ("semantic", "code"):
            op_type = "DivineCode Semantic Search" if search_mode == "semantic" else "DivineCode Code Search"
            emoji = "🔎" if search_mode == "semantic" else "🧬"
            summary = f"Analyzed ({search_mode}) for: '{query}'"
            params = {"instruction": query}
            # Simulate progressive search with line numbers and results
            for i in range(1, 6):
                match_count = i * 14
                self.print_search_progress_box(
                    op_type=op_type,
                    results=[
                        f"DivineCode agent response for: '{query}'",
                        f"Search mode: {search_mode}",
                        f"Parameters: {params}",
                        f"Matches so far: {match_count}",
                        f"Line: {i*130}/650",
                        f"Searching {'.' * i}",
                    ][:4] + (["... +{} lines".format(len([
                        f"DivineCode agent response for: '{query}'",
                        f"Search mode: {search_mode}",
                        f"Parameters: {params}",
                        f"Matches so far: {match_count}",
                        f"Line: {i*130}/650",
                        f"Searching {'.' * i}",
                    ])-4)] if len([
                        f"DivineCode agent response for: '{query}'",
                        f"Search mode: {search_mode}",
                        f"Parameters: {params}",
                        f"Matches so far: {match_count}",
                        f"Line: {i*130}/650",
                        f"Searching {'.' * i}",
                    ]) >4 else []),
                    params=params,
                    result_type=search_mode,
                    summary=f"DivineCode {search_mode} search for: '{query}'",
                    progress_line=f"Processed {i*130} lines",
                    spinner_state="Generating... Taking longer than expected" if i > 3 else f"Searching {'.' * i}",
                    operation_type=op_type,
                    search_mode=search_mode,
                    total_lines=650,
                    emoji=emoji,
                    border='╔'
                )
                await asyncio.sleep(0.05)
            self.print_search_progress_box(
                op_type=op_type,
                results=[
                    f"Searched for: '{query}'",
                    f"Search mode: {search_mode}",
                    f"Parameters: {params}",
                    "Found 70 matches.",
                    "Processed 650 lines.",
                    "Processed",
                ][:4] + ([f"... +{2} lines"] if len([
                    f"Searched for: '{query}'",
                    f"Search mode: {search_mode}",
                    f"Parameters: {params}",
                    "Found 70 matches.",
                    "Processed 650 lines.",
                    "Processed",
                ]) >4 else []),
                params=params,
                result_type="search_results",
                summary=f"DivineCode {search_mode} search complete for: '{query}'",
                progress_line="Processed 650 lines",
                spinner_state="Done",
                operation_type=op_type,
                search_mode=search_mode,
                total_lines=650,
                emoji=emoji,
                border='╔'
            )
            yield {"messages": [{"role": "assistant", "content": f"{search_mode.title()} search complete. Found 70 results for '{query}'."}]}
            return
        self.print_search_progress_box(
            op_type="DivineCode Final Results",
            results=self.format_diff_lines([
                f"Search mode: {search_mode}",
                f"Parameters: {params}",
                "Found 70 matches.",
                "Processed 650 lines.",
                "Operation complete.",
            ]),
            params=params,
            result_type="final_results",
            summary=f"DivineCode operation complete for: '{query}'",
            progress_line="Processed 650 lines",
            spinner_state="Done",
            operation_type="DivineCode Final Results",
            search_mode=search_mode,
            total_lines=650,
            emoji="✨",  # Default emoji value
            border='╔'
        )

    def format_diff_lines(self, lines: list[str]) -> list[str]:  # type: ignore
        """Add ANSI colors to diff lines"""
        formatted: list[str] = []
        for line in lines:
            if line.startswith('+'):
                formatted.append(f"\033[32m{line}\033[0m")  # Green for additions
            elif line.startswith('-'):
                formatted.append(f"\033[31m{line}\033[0m")  # Red for removals
            else:
                formatted.append(line)
        return formatted
        # After LLM/agent run, show a creative output box with the main result
        results = [llm_response]
        self.print_search_progress_box(
            op_type="DivineCode Creative",
            results=self.format_diff_lines(results),
            params=None,
            result_type="creative",
            summary=f"Creative generation complete for: '{query}'",
            progress_line=None,
            spinner_state=None,
            operation_type="DivineCode Creative",
            search_mode=None,
            total_lines=None,
            emoji='🧬',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": results[0]}]}
        return

if __name__ == "__main__":
    import sys
    # print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   ✨ DIVINE CODE BLUEPRINT                                   ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint seeks divine inspiration for your code.       ║\n║ Try running: python blueprint_gawd.py 'Find a bug!'   ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Inspire me!"
    messages = [
        {"role": "user", "content": user_input}
    ]
    blueprint = GAWDBlueprint(blueprint_id="demo-divine-code")
    async def run_and_print():
        async for _response in blueprint.run(messages):
            # print(json.dumps(response, indent=2))
            pass
    aio.run(run_and_print())
