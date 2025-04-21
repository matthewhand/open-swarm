import asyncio

from blueprint_whinge_surf import WhingeSurfBlueprint


def main():
    print("WhingeSurf CLI (type !run <cmd> or !status <proc_id>, or 'exit' to quit)")
    blueprint = WhingeSurfBlueprint(blueprint_id="cli-whinge-surf")
    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = input("whinge> ").strip()
            if user_input.lower() in ("exit", "quit"): break
            if not user_input:
                continue
            messages = [{"role": "user", "content": user_input}]
            # Only prompt to press enter if a response is being generated
            print("[Generating response... press Enter to continue if nothing appears]")
            async def run_and_print():
                async for chunk in blueprint.run(messages):
                    if chunk and "messages" in chunk:
                        for msg in chunk["messages"]:
                            print(msg["content"])
            loop.run_until_complete(run_and_print())
        except KeyboardInterrupt:
            print("\nExiting WhingeSurf CLI.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
