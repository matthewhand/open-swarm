#!/usr/bin/env python3
"""
Suggestion Blueprint CLI wrapper.

Usage:
  suggestion --message "Your prompt here"
"""
import argparse
import asyncio
import json
import os
import sys

from swarm.blueprints.suggestion.blueprint_suggestion import SuggestionBlueprint


def parse_args():
    parser = argparse.ArgumentParser(description="Suggestion Blueprint CLI — structured JSON suggestions")
    parser.add_argument('--message', '-m', type=str, help='Instruction for suggestions', required=False)
    return parser.parse_args()

def main():
    args = parse_args()
    instruction = args.message
    if not instruction:
        try:
            instruction = input("Instruction: ")
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
    if not instruction:
        print("No instruction provided. Exiting.")
        sys.exit(1)

    # Test mode: print example JSON and exit early
    if os.environ.get('SWARM_TEST_MODE'):
        example = {
            "suggestions": [
                "What are the potential ethical implications of AI adoption?",
                "How can we ensure transparency in AI decision-making?",
                "What safeguards are necessary for AI deployment in critical systems?"
            ]
        }
        print(json.dumps(example, indent=2))
        sys.exit(0)
    # Instantiate the blueprint
    bp = SuggestionBlueprint(blueprint_id="suggestion")
    messages = [{"role": "user", "content": instruction}]

    # Run and print structured suggestions
    async def run_and_print():
        async for chunk in bp.run(messages):
            # Extract the JSON content from the last message
            msgs = chunk.get('messages', [])
            if not msgs:
                continue
            content = msgs[-1].get('content', '').strip()
            print(content)

    asyncio.run(run_and_print())

if __name__ == '__main__':
    main()
