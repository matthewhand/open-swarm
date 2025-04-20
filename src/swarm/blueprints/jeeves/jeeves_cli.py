import argparse
import asyncio
from swarm.blueprints.jeeves.blueprint_jeeves import JeevesBlueprint, JeevesSpinner, display_operation_box, SPINNER_STATES

def main():
    parser = argparse.ArgumentParser(description="Jeeves: Home automation and web search butler")
    parser.add_argument("--instruction", type=str, help="Instruction for Jeeves to execute", default=None)
    parser.add_argument("--message", dest='instruction', type=str, help="Instruction for Jeeves agent (alias --message)")
    args = parser.parse_args()
    bp = JeevesBlueprint(blueprint_id="jeeves")

    async def run_instruction(instruction):
        spinner = JeevesSpinner()
        spinner.start()
        try:
            messages = [{"role": "user", "content": instruction}]
            spinner_idx = 0
            import time
            spinner_start = time.time()
            async for chunk in bp.run(messages):
                if isinstance(chunk, dict) and (chunk.get("progress") or chunk.get("matches")):
                    elapsed = time.time() - spinner_start
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
        messages = [{"role": "user", "content": args.instruction}]
        asyncio.run(run_instruction(args.instruction))
    else:
        print("[Jeeves CLI] Type your instruction and press Enter. Ctrl+C to exit.")
        try:
            while True:
                user_input = input("You: ")
                if user_input.strip():
                    asyncio.run(run_instruction(user_input.strip()))
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Jeeves CLI.")

if __name__ == "__main__":
    main()
