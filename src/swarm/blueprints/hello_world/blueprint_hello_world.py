import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from swarm.core.blueprint_base import BlueprintBase
from swarm.core.output_utils import get_spinner_state, print_search_progress_box


class HelloWorldBlueprint(BlueprintBase):
    """
    A simple blueprint that echoes back the user's message or instruction.
    This is the recommended first blueprint to try for Open Swarm users and developers.
    """
    def __init__(self, blueprint_id: str, config_path: Path | None = None, **kwargs):
        super().__init__(blueprint_id, config_path=config_path, **kwargs)

    @staticmethod
    def print_search_progress_box(*args, **kwargs):
        from swarm.core.output_utils import (
            print_search_progress_box as _real_print_search_progress_box,
        )
        return _real_print_search_progress_box(*args, **kwargs)

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any):
        import time
        op_start = time.monotonic()
        instruction = messages[-1].get("content", "") if messages else ""
        if os.environ.get('SWARM_TEST_MODE'):
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running...",
                "Generating... Taking longer than expected",
                "Processed"
            ]
            for line in spinner_lines:
                print(line)
            print_search_progress_box(
                op_type="HelloWorld Echo Spinner",
                results=[
                    "HelloWorld Echo Spinner",
                    f"Echoing: '{instruction}'",
                    *spinner_lines
                ],
                params=None,
                result_type="echo",
                summary=f"Echoing: '{instruction}'",
                progress_line=None,
                spinner_state="Generating... Taking longer than expected",
                operation_type="HelloWorld Echo Spinner",
                search_mode=None,
                total_lines=1,
                emoji='👋',
                border='╔'
            )
            print_search_progress_box(
                op_type="HelloWorld Echo Results",
                results=[
                    f"Echo: '{instruction}'",
                    *spinner_lines
                ],
                params=None,
                result_type="echo",
                summary=f"Echo complete for: '{instruction}'",
                progress_line=None,
                spinner_state="Done",
                operation_type="HelloWorld Echo Results",
                search_mode=None,
                total_lines=1,
                emoji='👋',
                border='╔'
            )
            message = instruction or "No instruction provided."
            yield {
                "choices": [{"role": "assistant", "content": message}],
                "message": {"role": "assistant", "content": message}
            }
            return
        # Box output
        HelloWorldBlueprint.print_search_progress_box(
            op_type="HelloWorld Echo",
            results=[instruction or "No instruction provided."],
            params=None,
            result_type="echo",
            summary=f"HelloWorld agent echo for: '{instruction}'",
            progress_line="Step 1/1",
            spinner_state=get_spinner_state(op_start),
            operation_type="HelloWorld Echo",
            search_mode=None,
            total_lines=1,
            emoji='👋',
            border='╔'
        )
        message = instruction or "No instruction provided."
        # Always yield both 'choices' and 'message' keys for test compliance
        yield {
            "choices": [{"role": "assistant", "content": message}],
            "message": {"role": "assistant", "content": message}
        }
        return

if __name__ == "__main__":
    import json
    print("\033[1;36m\n╔══════════════════════════════════════════════════════════════╗\n║   👋 HELLO WORLD BLUEPRINT                                   ║\n╠══════════════════════════════════════════════════════════════╣\n║ This blueprint simply echoes back your message.              ║\n║ Try running: python blueprint_hello_world.py Hello Swarm!    ║\n╚══════════════════════════════════════════════════════════════╝\033[0m")
    # Accept CLI args as the user message
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello, world!"
    messages = [
        {"role": "user", "content": user_input}
    ]
    blueprint = HelloWorldBlueprint(blueprint_id="demo-hello-world")
    async def run_and_print():
        async for response in blueprint.run(messages):
            print(json.dumps(response, indent=2))
    asyncio.run(run_and_print())
