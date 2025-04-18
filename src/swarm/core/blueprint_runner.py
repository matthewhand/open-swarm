import sys
import traceback
import types
from typing import AsyncGenerator
import inspect

from .blueprint_base import Spinner

class BlueprintRunner:
    @staticmethod
    async def run_agent(agent, instruction, filter_llm_function_calls=True, spinner_enabled=True) -> AsyncGenerator[dict, None]:
        """
        Runs the agent using Runner.run as an async generator or coroutine, with spinner and error handling.
        Filters out LLM function call outputs if requested.
        Handles both coroutine and async generator return types.
        """
        from agents import Runner
        # Only enable spinner if spinner_enabled is True and not in non-interactive mode
        # (i.e., only if show_intermediate is True)
        spinner = None
        if spinner_enabled:
            # Check for a marker in instruction or a kwarg to disable spinner in non-interactive
            frame = inspect.currentframe()
            show_intermediate = False
            while frame:
                if 'kwargs' in frame.f_locals and isinstance(frame.f_locals['kwargs'], dict):
                    show_intermediate = frame.f_locals['kwargs'].get('show_intermediate', False)
                    break
                frame = frame.f_back
            if show_intermediate:
                spinner = Spinner()
        try:
            if spinner:
                spinner.start()
            result = await Runner.run(agent, instruction)
            # If result is an async generator, iterate over it
            if isinstance(result, types.AsyncGeneratorType):
                async for chunk in result:
                    if filter_llm_function_calls:
                        content = chunk.get("content")
                        if content and ("function call" in content or "args" in content):
                            continue
                    yield chunk
            elif isinstance(result, (list, dict)):
                # If it's a list of chunks or a single chunk, yield directly
                if isinstance(result, list):
                    for chunk in result:
                        yield chunk
                else:
                    yield result
            elif result is not None:
                # Fallback: yield as a single chunk
                yield {"messages": [{"role": "assistant", "content": str(result)}]}
        except Exception as e:
            tb = traceback.format_exc()
            yield {"messages": [{"role": "assistant", "content": f"Error: {e}\n{tb}"}]}
        finally:
            if spinner:
                spinner.stop()
