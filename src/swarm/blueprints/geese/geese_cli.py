import argparse
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint
import asyncio
import time
import os
import sys
from swarm.core.output_utils import print_operation_box as display_operation_box 
from swarm.core.interaction_types import AgentInteraction # For type checking

SPINNER_STATES = ["Generating.", "Generating..", "Generating...", "Running..."] 
SLOW_SPINNER = "Generating... Taking longer than expected" 

def main():
    parser = argparse.ArgumentParser(description="Run the Geese Blueprint")
    parser.add_argument('--message', dest='prompt', nargs='?', default=None, help='Prompt for the agent')
    parser.add_argument('--config', type=str, help='Path to config file', default=None)
    parser.add_argument('--agent-mcp', action='append', help='Agent to MCP assignment, e.g. --agent-mcp agent1:mcpA,mcpB')
    parser.add_argument('--model', type=str, help='Model name (overrides DEFAULT_LLM envvar)', default=None)
    args = parser.parse_args()

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
        agent_mcp_assignments=agent_mcp_assignments,
        llm_model=args.model 
    )

    messages = []
    if args.prompt:
        messages.append({"role": "user", "content": args.prompt})
    else: # Fallback to interactive input if no --message
        print("[Geese CLI] No prompt provided via --message. Enter prompt (or 'quit'/'exit'):")
        try:
            user_input = input("Prompt: ")
            if user_input.lower() in ['quit', 'exit'] or not user_input.strip():
                print("Exiting.")
                return
            messages = [{"role": "user", "content": user_input.strip()}]
        except EOFError:
            print("\nNo input. Exiting.")
            return
            
    async def run_and_print():
        print(f"Running Geese blueprint with prompt: {messages[-1]['content'] if messages else 'N/A'}")
        
        async for chunk in blueprint.run(messages):
            if isinstance(chunk, dict):
                chunk_type = chunk.get("type")
                if chunk_type == "spinner_update" and os.environ.get("SWARM_TEST_MODE") == "1":
                    # Test mode expects [SPINNER] prefix, which blueprint_geese.py now adds to spinner_state
                    print(chunk.get("spinner_state", "Processing...")) 
                elif chunk_type == "progress":
                    # Normal progress update for non-test mode CLI
                    # This part would use display_operation_box or similar rich output
                    progress_msg = chunk.get("progress_message", "Working...")
                    spinner_char = chunk.get("spinner_state", SPINNER_STATES[0]) # Default spinner
                    sys.stdout.write(f"\r{spinner_char} {progress_msg}   ")
                    sys.stdout.flush()
                elif chunk_type == "message" and chunk.get("role") == "assistant":
                    content = chunk.get("content", "")
                    # Clear spinner line before printing final message
                    sys.stdout.write(f"\r{' ' * 80}\r") # Clear line
                    print(f"Geese: {content}")
                    if chunk.get("final") and chunk.get("data"):
                        story_data = chunk.get("data")
                        if isinstance(story_data, dict): # If data is StoryOutput as dict
                             print(f"  (Title: {story_data.get('title', 'N/A')}, Word Count: {story_data.get('word_count', 0)})")
                elif chunk_type == "error":
                    sys.stdout.write(f"\r{' ' * 80}\r")
                    print(f"\nError: {chunk.get('error_message', 'Unknown error')}")
                else: # Fallback for other dict structures
                    sys.stdout.write(f"\r{' ' * 80}\r")
                    print(f"Geese (raw dict): {chunk}")
            elif isinstance(chunk, str): # Fallback for simple string yields
                sys.stdout.write(f"\r{' ' * 80}\r")
                print(f"Geese: {chunk}")
            else:
                sys.stdout.write(f"\r{' ' * 80}\r")
                print(f"Geese (unknown type): {chunk}")
        
        sys.stdout.write(f"\r{' ' * 80}\r") # Clear any final spinner line
        print("Geese run complete.")

    asyncio.run(run_and_print())

if __name__ == "__main__":
    main()
