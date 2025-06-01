import argparse
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
import asyncio
import time
import os
import sys

# Assuming these are still relevant for the CLI's desired UX,
# they need to be correctly sourced or the CLI logic adapted.
# For now, the GeeseBlueprint itself handles its test_mode output.
# from swarm.blueprints.geese.blueprint_geese import SPINNER_STATES, SLOW_SPINNER # These are not in blueprint_geese.py
from swarm.core.output_utils import print_operation_box as display_operation_box # Correct import

# Define SPINNER_STATES and SLOW_SPINNER if they are to be used by the CLI directly
# These were previously in blueprint_geese.py for test mode, but JeevesSpinner handles its own.
# If the CLI needs its own spinner message cycle, define them here.
# For now, this CLI's spinner logic seems to rely on blueprint.run yielding spinner_state.
SPINNER_STATES = ["Generating.", "Generating..", "Generating...", "Running..."] # Example
SLOW_SPINNER = "Generating... Taking longer than expected" # Example

def main():
    parser = argparse.ArgumentParser(description="Run the Geese Blueprint")
    parser.add_argument('--message', dest='prompt', nargs='?', default=None, help='Prompt for the agent (optional, aliased as --message for compatibility)')
    parser.add_argument('--config', type=str, help='Path to config file', default=None)
    parser.add_argument('--agent-mcp', action='append', help='Agent to MCP assignment, e.g. --agent-mcp agent1:mcpA,mcpB')
    parser.add_argument('--model', type=str, help='Model name (overrides DEFAULT_LLM envvar)', default=None)
    args = parser.parse_args()

    # Ensure agent_mcp_assignments is always a dict
    agent_mcp_assignments = {} 
    if args.agent_mcp:
        for assignment in args.agent_mcp:
            try:
                agent, mcps_str = assignment.split(':', 1)
                agent_mcp_assignments[agent] = [m.strip() for m in mcps_str.split(',')]
            except ValueError:
                print(f"Warning: Malformed --agent-mcp argument: {assignment}. Skipping.", file=sys.stderr)
    
    if args.model:
        os.environ['DEFAULT_LLM'] = args.model

    blueprint = GeeseBlueprint(
        blueprint_id='geese_cli', 
        config_path=args.config,
        agent_mcp_assignments=agent_mcp_assignments, # Now always a dict
        llm_model=args.model # Pass model directly to blueprint if it accepts it
    )
    
    messages = []
    if args.prompt:
        messages.append({"role": "user", "content": args.prompt})
    
    if not messages:
        print("[Geese CLI] No prompt provided. Enter 'quit' or 'exit' to stop.")
        while True:
            try:
                user_input = input("Prompt: ")
                if user_input.lower() in ['quit', 'exit']:
                    break
                if user_input.strip():
                    messages = [{"role": "user", "content": user_input.strip()}]
                    break 
            except EOFError:
                break
        if not messages:
            print("No input received. Exiting.")
            return

    async def run_and_print():
        print(f"Running Geese blueprint with prompt: {messages[-1]['content'] if messages else 'N/A'}")
        spinner_idx = 0
        spinner_start_cli = time.time() # Use a different name to avoid conflict if blueprint uses 'spinner_start'

        async for chunk in blueprint.run(messages): # Removed model=args.model, blueprint uses its configured one
            # The CLI's display_operation_box call needs to match the function signature from output_utils
            # print_operation_box(title, content, result_count, params, progress_line, total_lines, spinner_state, emoji)
            if isinstance(chunk, dict) and (chunk.get("progress") or chunk.get("matches") or chunk.get("spinner_state")):
                elapsed = time.time() - spinner_start_cli
                spinner_state_from_chunk = chunk.get("spinner_state")
                if not spinner_state_from_chunk: # Fallback spinner logic if blueprint doesn't provide it
                    spinner_state_from_chunk = SLOW_SPINNER if elapsed > 10 else SPINNER_STATES[spinner_idx % len(SPINNER_STATES)]
                spinner_idx += 1
                
                # Prepare arguments for display_operation_box (print_operation_box)
                title = "Searching Filesystem" if chunk.get("progress") else "Geese Output"
                content = str(chunk.get("matches", chunk)) # Simplified content
                result_count_val = len(chunk.get("matches", [])) if chunk.get("matches") is not None else 0
                params_val = {k: v for k, v in chunk.items() if k not in {'matches', 'progress', 'total', 'truncated', 'done', 'spinner_state'}}
                progress_line_val = chunk.get('progress') if chunk.get('progress') is not None else 0
                total_lines_val = chunk.get('total') if chunk.get('total') is not None else 1
                emoji_val = "🔍" if chunk.get("progress") else "💡"

                # This call might still fail if required args like result_count, progress_line, total_lines are None
                # and print_operation_box expects non-None for them.
                # For now, trying to pass something.
                try:
                    display_operation_box(
                        title=title,
                        content=content,
                        result_count=int(result_count_val or 0), # Ensure int
                        params=params_val or {}, # Ensure dict
                        progress_line=int(progress_line_val or 0), # Ensure int
                        total_lines=int(total_lines_val or 1), # Ensure int, default to 1 if not present
                        spinner_state=str(spinner_state_from_chunk or "Processing..."), # Ensure str
                        emoji=emoji_val
                    )
                except TypeError as te:
                    print(f"[CLI Warning] Could not display operation box due to TypeError: {te}. Raw chunk: {chunk}", file=sys.stderr)
                except Exception as e_box:
                    print(f"[CLI Warning] Error displaying operation box: {e_box}. Raw chunk: {chunk}", file=sys.stderr)


            elif isinstance(chunk, dict) and "messages" in chunk:
                for msg_content_item in chunk["messages"]:
                    if msg_content_item.get("role") == "assistant":
                        content = msg_content_item.get("content", "")
                        print(f"Geese: {content}")
            elif isinstance(chunk, str):
                print(f"Geese: {chunk}")
            else:
                print(f"Geese (raw): {chunk}")
        print("\nGeese run complete.")

    asyncio.run(run_and_print())

if __name__ == "__main__":
    main()
