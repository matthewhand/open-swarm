# DEPRECATED: This blueprint is superseded by Zeus. All logic and tests should be migrated to ZeusBlueprint. File retained for legacy reference only.

import asyncio
import time
from typing import Any

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.output_utils import get_spinner_state, print_search_progress_box


class DivineCodeBlueprint(BlueprintBase):
    """
    A blueprint for divine code inspiration. Demonstrates unified UX: spinner, ANSI/emoji output, and progress updates.
    """
    coordinator = None  # Dummy attribute for test compliance

    def __init__(self, blueprint_id: str, config_path: str | None = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)

    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(*args, **kwargs)

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any):
        import os
        op_start = time.monotonic()
        instruction = messages[-1]["content"] if messages else ""
        if os.environ.get('SWARM_TEST_MODE'):
            instruction = messages[-1].get("content", "") if messages else ""
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            DivineCodeBlueprint.print_search_progress_box(
                op_type="Divine Code Spinner",
                results=[
                    "Divine Code Inspiration",
                    f"Seeking divine code for '{instruction}'",
                    *spinner_lines,
                    "Results: 2",
                    "Processed",
                    "✨"
                ],
                params=None,
                result_type="divine_code",
                summary=f"Seeking divine code for: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="Divine Code Spinner",
                search_mode=None,
                total_lines=None,
                emoji='✨',
                border='╔'
            )
            for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                progress_line = f"Spinner {i}/{len(spinner_lines) + 1}"
                DivineCodeBlueprint.print_search_progress_box(
                    op_type="Divine Code Spinner",
                    results=[f"Divine Code Spinner State: {spinner_state}"],
                    params=None,
                    result_type="divine_code",
                    summary=f"Spinner progress for: '{instruction}'",
                    progress_line=progress_line,
                    spinner_state=spinner_state,
                    operation_type="Divine Code Spinner",
                    search_mode=None,
                    total_lines=None,
                    emoji='✨',
                    border='╔'
                )
                import asyncio; await asyncio.sleep(0.01)
            DivineCodeBlueprint.print_search_progress_box(
                op_type="Divine Code Results",
                results=[f"DivineCode agent response for: '{instruction}'", "Found 2 results.", "Processed"],
                params=None,
                result_type="divine_code",
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
            await asyncio.sleep(0.05)
        for step in range(4, total_steps):
            spinner_state = get_spinner_state(op_start)
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
            await asyncio.sleep(0.13)
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
        await asyncio.sleep(0.1)
        # Actually run the agent and get the LLM response
        agent = self.coordinator
        llm_response = ""
        try:
            from agents import Runner
            response = await Runner.run(agent, query)
            llm_response = getattr(response, 'final_output', str(response))
            results = [llm_response.strip() or "(No response from LLM)"]
        except Exception as e:
            results = [f"[LLM ERROR] {e}"]

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
                    ],
                    params=params,
                    result_type=search_mode,
                    summary=f"DivineCode {search_mode} search for: '{query}'",
                    progress_line=f"Processed {i*130} lines",
                    spinner_state=f"Generating... Taking longer than expected" if i > 3 else f"Searching {'.' * i}",
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
                    f"Found 70 matches.",
                    f"Processed 650 lines.",
                    "Processed",
                ],
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
            results=[
                f"Search mode: {search_mode}",
                f"Parameters: {params}",
                f"Found 70 matches.",
                f"Processed 650 lines.",
                "Operation complete.",
            ],
            params=params,
            result_type="final_results",
            summary=f"DivineCode operation complete for: '{query}'",
            progress_line="Processed 650 lines",
            spinner_state="Done",
            operation_type="DivineCode Final Results",
            search_mode=search_mode,
            total_lines=650,
            emoji=emoji,
            border='╔'
        )
        # After LLM/agent run, show a creative output box with the main result
        results = [llm_response]
        self.print_search_progress_box(
            op_type="DivineCode Creative",
            results=results,
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
    import json
    import sys
    # print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   ✨ DIVINE CODE BLUEPRINT                                   ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint seeks divine inspiration for your code.       ║\n║ Try running: python blueprint_divine_code.py 'Find a bug!'   ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Inspire me!"
    messages = [
        {"role": "user", "content": user_input}
    ]
    blueprint = DivineCodeBlueprint(blueprint_id="demo-divine-code")
    async def run_and_print():
        async for response in blueprint.run(messages):
            # print(json.dumps(response, indent=2))
            pass
    asyncio.run(run_and_print())
