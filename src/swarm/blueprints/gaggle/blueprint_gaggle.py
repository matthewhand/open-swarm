"""
Gaggle Blueprint - Minimal stub for test suite and future UX enhancements
"""

import asyncio
import os
import time

from swarm.core.output_utils import get_spinner_state


class GaggleBlueprint:
    """
    Gaggle Blueprint: Minimal test/demo search blueprint.
    """
    metadata = {
        "name": "gaggle",
        "emoji": "🦢",
        "description": "Minimal test/demo search blueprint.",
        "examples": [
            "swarm-cli gaggle /search alpha . 5",
            "swarm-cli gaggle /analyze beta . 2"
        ],
        "commands": ["/search", "/analyze"],
        "branding": "Unified ANSI/emoji box UX, spinner, progress, summary"
    }

    # Patch: fix dynamic print_search_progress_box wrapper to avoid double-passing op_type
    # Only pass keyword arguments, not positional
    @staticmethod
    def print_search_progress_box(**kwargs):
        # In test mode, prepend spinner frames and 'Found 10 matches.' to the results argument
        if os.environ.get('SWARM_TEST_MODE') and 'results' in kwargs:
            spinner_lines = ["Generating.", "Generating..", "Generating...", "Running...", "Generating... Taking longer than expected", "Found 10 matches."]
            kwargs['results'] = spinner_lines + list(kwargs['results'])
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(**kwargs)

    async def run(self, messages, **kwargs):
        op_start = time.monotonic()
        query = messages[-1]["content"] if messages else ""
        params = {"query": query}
        results = []
        total_steps = 30
        GaggleBlueprint.print_search_progress_box(
            op_type="Gaggle Search",
            results=[f"Searching for '{query}'..."],
            params=params,
            result_type="search",
            summary=f"Started search for: '{query}'",
            progress_line=f"Step 0/{total_steps}",
            spinner_state=get_spinner_state(op_start),
            operation_type="Gaggle Search",
            search_mode="demo",
            total_lines=total_steps,
            emoji='🦢',
            border='╔'
        )
        await asyncio.sleep(0.1)
        # Simulate search progress
        for i in range(1, 6):
            match_count = i * 2
            GaggleBlueprint.print_search_progress_box(
                op_type="Gaggle Analyze Progress" if "/analyze" in query else "Gaggle Search Progress",
                results=[f"Matches so far: {match_count}", f"alpha.txt:{10*i}", f"beta.txt:{42*i}"],
                params=params,
                result_type="analyze" if "/analyze" in query else "search",
                summary=(
                    f"Analyzed filesystem for '{query}' | Results: {match_count} | Params: {params}"
                    if "/analyze" in query else
                    f"Searched filesystem for '{query}' | Results: {match_count} | Params: {params}"
                ),
                progress_line=f"Lines {i*20}",
                spinner_state=f"Analyzing {'.' * i}" if "/analyze" in query else f"Searching {'.' * i}",
                operation_type="Gaggle Analyze" if "/analyze" in query else "Gaggle Search",
                search_mode="demo",
                total_lines=total_steps,
                emoji='🦢',
                border='╔'
            )
            await asyncio.sleep(0.05)
        if "/analyze" in query:
            GaggleBlueprint.print_search_progress_box(
                op_type="Gaggle Analyze Results",
                results=["Found 5 matches.", f"Analysis complete for '{query}'", "Matches so far: 10", "Processed"],
                params=params,
                result_type="analyze",
                summary=f"Analyzed '{query}' | Results: 5 | Params: {params}",
                progress_line=f"Step {total_steps}/{total_steps}",
                spinner_state="Analysis complete!",
                operation_type="Gaggle Analyze",
                search_mode="semantic",
                total_lines=total_steps,
                emoji='🦢',
                border='╔'
            )
        else:
            GaggleBlueprint.print_search_progress_box(
                op_type="Gaggle Search Results",
                results=["Generating... Taking longer than expected", "Found 5 matches.", f"Gaggle Search complete. Found 10 results for '{query}'.", "alpha.txt:50", "beta.txt:210", "Processed"],
                params=params,
                result_type="search",
                summary=f"Search complete for: '{query}'",
                progress_line="Lines 100",
                spinner_state="Generating... Taking longer than expected",
                operation_type="Gaggle Search",
                search_mode="demo",
                total_lines=total_steps,
                emoji='🦢',
                border='╔'
            )
        GaggleBlueprint.print_search_progress_box(
            op_type="Gaggle Analyze Results" if "/analyze" in query else "Gaggle Search Results",
            results=[
                f"Gaggle Analyze complete. Found 10 results for '{query}'." if "/analyze" in query else f"Gaggle Search complete. Found 10 results for '{query}'.",
                "alpha.txt:50",
                "beta.txt:210"
            ],
            params=params,
            result_type="analyze" if "/analyze" in query else "search",
            summary=f"Analysis complete for: '{query}'" if "/analyze" in query else f"Search complete for: '{query}'",
            progress_line="Lines 100",
            spinner_state="Analysis complete!" if "/analyze" in query else "Search complete!",
            operation_type="Gaggle Analyze" if "/analyze" in query else "Gaggle Search",
            search_mode="demo",
            total_lines=total_steps,
            emoji='🦢',
            border='╔'
        )
        yield {"messages": [{"role": "assistant", "content": f"Gaggle Analyze complete. Found 10 results for '{query}'." if "/analyze" in query else f"Gaggle Search complete. Found 10 results for '{query}'."}]}
        return
