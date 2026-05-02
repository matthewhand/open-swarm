import inspect
import traceback
import types
from collections.abc import AsyncGenerator

from .blueprint_base import Spinner


class BlueprintRunner:
    @staticmethod
    async def run_agent(agent, instruction, filter_llm_function_calls=True, spinner_enabled=True) -> AsyncGenerator[dict, None]:
        """
        Runs the agent using Runner.run as an async generator or coroutine, with spinner and error handling.
        Filters out LLM function call outputs if requested.
        Handles both coroutine and async generator return types.
        Injects memory context if available and saves the response.
        """
        from agents import Runner
        
        # --- Memory Integration: Inject Context ---
        memory_instance = getattr(agent, "memory", None)
        original_instructions = agent.instructions
        if memory_instance:
            try:
                # Search memory for relevant context
                context = memory_instance.search(instruction)
                if context:
                    if isinstance(context, list):
                        context_str = "\n".join([c.get("content", "") if isinstance(c, dict) else str(c) for c in context])
                    else:
                        context_str = str(context)
                    
                    # Inject into instructions
                    agent.instructions = f"{original_instructions}\n\n[MEMORY CONTEXT]\n{context_str}\n[/MEMORY CONTEXT]"
            except Exception as e:
                # Log error but don't fail the run
                print(f"[MEMORY ERROR] Failed to search memory: {e}")

        # Only enable spinner if spinner_enabled is True and not in non-interactive mode
        spinner = None
        if spinner_enabled:
            frame = inspect.currentframe()
            show_intermediate = False
            while frame:
                if 'kwargs' in frame.f_locals and isinstance(frame.f_locals['kwargs'], dict):
                    show_intermediate = frame.f_locals['kwargs'].get('show_intermediate', False)
                    break
                frame = frame.f_back
            if show_intermediate:
                spinner = Spinner()
        
        full_response = ""
        try:
            if spinner:
                spinner.start()
            
            # Save user instruction to memory
            if memory_instance:
                try:
                    memory_instance.add(instruction, metadata={"role": "user"})
                except Exception as e:
                    print(f"[MEMORY ERROR] Failed to save user instruction: {e}")

            result = await Runner.run(agent, instruction)
            
            # If result is an async generator, iterate over it
            if isinstance(result, types.AsyncGeneratorType):
                async for chunk in result:
                    content = chunk.get("content") or ""
                    if filter_llm_function_calls:
                        if content and ("function call" in content or "args" in content):
                            continue
                    full_response += content
                    yield chunk
            elif isinstance(result, list | dict):
                # If it's a list of chunks or a single chunk, yield directly
                if isinstance(result, list):
                    for chunk in result:
                        content = chunk.get("content") or ""
                        full_response += content
                        yield chunk
                else:
                    content = result.get("content") or ""
                    full_response += content
                    yield result
            elif result is not None:
                # Fallback: yield as a single chunk
                content = str(result)
                full_response += content
                yield {"messages": [{"role": "assistant", "content": content}]}
            
            # --- Memory Integration: Save Response ---
            if memory_instance and full_response:
                try:
                    memory_instance.add(full_response, metadata={"role": "assistant"})
                except Exception as e:
                    print(f"[MEMORY ERROR] Failed to save response to memory: {e}")

        except Exception as e:
            tb = traceback.format_exc()
            yield {"messages": [{"role": "assistant", "content": f"Error: {e}\n{tb}"}]}
        finally:
            # Restore original instructions
            agent.instructions = original_instructions
            if spinner:
                spinner.stop()
