import argparse
import asyncio
import sys
from swarm.blueprints.codey.blueprint_codey import CodeyBlueprint, CodeySpinner, display_operation_box
from swarm.extensions.cli.utils.async_input import AsyncInputHandler

def main():
    parser = argparse.ArgumentParser(description="Codey: Approval workflow demo")
    parser.add_argument("--message", type=str, help="User message to process", default=None)
    args = parser.parse_args()
    bp = CodeyBlueprint()

    if args.message:
        # Route through the agent's tool-calling logic
        print(f"Assisting with: {args.message}")
        import os
        if os.environ.get('SWARM_TEST_MODE') == '1':
            print('[DEBUG] SWARM_TEST_MODE=1 detected, using test spinner/progressive output')
            agent = CodeyBlueprint(blueprint_id="test_codey")
            print(f'[DEBUG] Forced agent: {agent.__class__.__name__}')
        else:
            bp = CodeyBlueprint()
            agents = bp.create_agents()
            agent = agents.get('codegen') or list(agents.values())[0]
            print(f'[DEBUG] Using agent: {agent.__class__.__name__}')
        messages = [{"role": "user", "content": args.message}]
        if hasattr(agent, 'run'):
            async def run_and_print():
                results = []
                async for chunk in agent.run(messages):
                    print(f'[DEBUG] Chunk: {chunk}')
                    spinner_state = chunk.get('spinner_state', '')
                    matches = chunk.get('matches', [])
                    progress = chunk.get('progress', None)
                    total = chunk.get('total', None)
                    # Output spinner state for testability
                    if spinner_state:
                        print(f"[SPINNER] {spinner_state}")
                    display_operation_box(
                        title="Code Search",
                        content=f"Matches so far: {len(matches)}",
                        result_count=len(matches),
                        params={},
                        progress_line=progress,
                        total_lines=total,
                        spinner_state=spinner_state,
                        emoji="💻"
                    )
                    results.append(chunk)
                return results
            try:
                asyncio.run(run_and_print())
            except Exception as e:
                print(f"error: {e}")
            return
        else:
            try:
                print(bp.assist(args.message))
            except Exception as e:
                print(f"error: {e}")
        return

    print("[Codey Interactive CLI]")
    print("Type your prompt and press Enter. Press Enter again to interrupt and send a new message.")

    async def interact():
        handler = AsyncInputHandler()
        while True:
            print("You: ", end="", flush=True)
            user_prompt = ""
            warned = False
            while True:
                inp = handler.get_input(timeout=0.1)
                if inp == 'warn' and not warned:
                    print("\n[!] Press Enter again to interrupt and send a new message.", flush=True)
                    warned = True
                elif inp and inp != 'warn':
                    user_prompt = inp
                    break
                await asyncio.sleep(0.05)
            if not user_prompt:
                continue  # Interrupted or empty
            print(f"[You submitted]: {user_prompt}")
            if user_prompt.strip().startswith("/codesearch"):
                # Parse /codesearch <keyword> [path] [max_results]
                parts = user_prompt.strip().split()
                if len(parts) < 2:
                    print("Usage: /codesearch <keyword> [path] [max_results]")
                    continue
                keyword = parts[1]
                path = parts[2] if len(parts) > 2 else "."
                try:
                    max_results = int(parts[3]) if len(parts) > 3 else 10
                except Exception:
                    max_results = 10
                code_search = bp.tool_registry.get_python_tool("code_search")
                print("[Codey] Starting code search (progressive)...")
                spinner = CodeySpinner()
                spinner.start()
                try:
                    for update in code_search(keyword, path, max_results):
                        display_operation_box(
                            title="Code Search",
                            content=f"Matches so far: {len(update.get('matches', []))}",
                            result_count=len(update.get('matches', [])),
                            params={k: v for k, v in update.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done'}},
                            progress_line=update.get('progress'),
                            total_lines=update.get('total'),
                            spinner_state=spinner.current_spinner_state(),
                            emoji="💻"
                        )
                finally:
                    spinner.stop()
                print("[Codey] Code search complete.")
                continue
            spinner = CodeySpinner()
            spinner.start()
            try:
                response = bp.assist(user_prompt)
            finally:
                spinner.stop()
            for token in response.split():
                print(f"Codey: {token}", end=" ", flush=True)
                await asyncio.sleep(0.2)
            print("\n")
            display_operation_box(
                title="Assist",
                content=response,
                result_count=1,
                params={},
                progress_line="",
                total_lines=1,
                spinner_state="",
                emoji="💻"
            )

    try:
        asyncio.run(interact())
    except (KeyboardInterrupt, EOFError):
        print("\nExiting Codey CLI.")

def print_splash():
    bp = CodeyBlueprint(blueprint_id="codey")
    print(bp.get_cli_splash())

if __name__ == "__main__":
    import sys
    # Only print splash if not running with --message
    if not any(arg.startswith("--message") for arg in sys.argv):
        print_splash()
    main()
