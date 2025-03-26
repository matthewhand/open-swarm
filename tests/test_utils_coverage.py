import pytest
from unittest.mock import patch
import os # <-- Added import os
from typing import List, Dict, Any

# Assuming mock logic is sufficient for coverage testing context
# Replace with actual imports if needed for specific tests
# from swarm.llm_clients.llm_client_base import LLMClientBase

# --- Centralized Mock Logic ---
def mock_get_token_count_logic(text: Any, model: str) -> int:
    if isinstance(text, dict) and text.get("role") == "system": return 1
    if isinstance(text, dict) and text.get("role") == "user": return 2
    if isinstance(text, dict) and text.get("role") == "assistant" and text.get("tool_calls"): return 3 # Asst + Tool Call
    if isinstance(text, dict) and text.get("role") == "tool": return 2 # Tool Result
    if isinstance(text, dict) and text.get("role") == "assistant": return 2 # Regular Asst
    return 1 # Default

# <-- Added import for truncate_message_history -->
from src.swarm.utils.context_utils import truncate_message_history
# <-- Commented out old import removed -->
# from swarm.extensions.blueprint.message_utils import truncate_preserve_pairs # Old import removed

# Simple tests for basic utils coverage - more detailed tests are elsewhere

@patch('src.swarm.utils.context_utils.get_token_count', mock_get_token_count_logic)
def test_truncate_preserve_pairs_basic():
    messages = [
        {"role": "system", "content": "S"},      # 1 token
        {"role": "user", "content": "U1"},       # 2 tokens
        {"role": "assistant", "content": "A1"},  # 2 tokens
        {"role": "user", "content": "U2"},       # 2 tokens
        {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]}, # 3 tokens
        {"role": "tool", "tool_call_id": "t1", "content": "T1R"}, # 2 tokens
        {"role": "assistant", "content": "A2"},  # 2 tokens
    ]
    # Total non-sys: 2+2+2+3+2+2 = 13. System = 1. Total = 14.
    # Target: max_tokens=10, max_messages=5
    # Expected kept (pairs):
    # A2 (idx 6, cost 2) -> Keep. Total = 2. Remain = 8.
    # T1R (idx 5, cost 2) Pair w/ A1_call (idx 4, cost 3) = 5. Fits (2+5=7 <= 8). Keep Pair. Total = 7. Remain = 1.
    # U2 (idx 3, cost 2) > Remain. Stop.
    # System (cost 1)
    # Final = [SYS, A1_call, T1R, A2]
    # Target: 4 messages (5 - 1 system), 9 tokens (10 - 1 system)

    max_tokens = 10; max_messages = 5
    # Keep A2 (2 tokens, 1 msg). Total=2, Msgs=1. Remain=7, Msgs=3
    # Keep Pair T1R(2)+A_call(3)=5. Total=7, Msgs=3. Remain=2, Msgs=1
    # Keep U2(2). Total=9, Msgs=4. Remain=0, Msgs=0. Stop.
    expected = [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "U2"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]},
        {"role": "tool", "tool_call_id": "t1", "content": "T1R"},
        {"role": "assistant", "content": "A2"},
    ]
    # --- Call the new function, setting mode ---
    os.environ["SWARM_TRUNCATION_MODE"] = "pairs"
    result = truncate_message_history(messages, "test-model", max_tokens, max_messages)
    if "SWARM_TRUNCATION_MODE" in os.environ: del os.environ["SWARM_TRUNCATION_MODE"]
    # --- End change ---
    assert result == expected, f"Expected {expected}, got {result}"

# Example test for another strategy (if needed for coverage)
# @patch('src.swarm.utils.context_utils.get_token_count', mock_get_token_count_logic)
# def test_truncate_simple_coverage():
#     messages = [ {"role": "system", "content": "S"}, {"role": "user", "content": "U1"}, {"role": "assistant", "content": "A1"}, {"role": "user", "content": "U2"}, {"role": "assistant", "content": "A2"}, ]
#     max_tokens = 6; max_messages = 4
#     # Target: 3 msgs, 5 tokens
#     # Simple: A2(2)->K T=2 R=3 | U2(2)->K T=4 R=1 | A1(2)>R Stop.
#     expected = [ {"role": "system", "content": "S"}, {"role": "user", "content": "U2"}, {"role": "assistant", "content": "A2"}, ]
#     os.environ["SWARM_TRUNCATION_MODE"] = "simple"
#     result = truncate_message_history(messages, "test-model", max_tokens, max_messages)
#     if "SWARM_TRUNCATION_MODE" in os.environ: del os.environ["SWARM_TRUNCATION_MODE"]
#     assert result == expected

# Add more basic tests for other utility functions if they exist and need coverage

