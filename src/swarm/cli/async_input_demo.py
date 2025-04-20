import asyncio
import time
from async_input import AsyncInputHandler

def on_interrupt(_):
    print("\n[!] Interrupted! Submitting new prompt...")

async def fake_stream_response():
    for i in range(1, 8):
        print(f"Bot: streaming token {i}...", flush=True)
        await asyncio.sleep(1)
    print("Bot: done!\n")

async def main():
    handler = AsyncInputHandler(on_interrupt=on_interrupt)
    while True:
        user_prompt = await handler.get_input()
        if user_prompt is None:
            # Interrupted, start new loop
            continue
        print(f"[You submitted]: {user_prompt}")
        # Simulate streaming response
        stream_task = asyncio.create_task(fake_stream_response())
        while not stream_task.done():
            # Allow user to interrupt during streaming
            if handler._interrupt_event.is_set():
                stream_task.cancel()
                break
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
