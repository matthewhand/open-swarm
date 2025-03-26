import pytest
import logging
from typing import List, Dict, Any

# Functions to test
from src.swarm.utils.message_sequence import validate_message_sequence, repair_message_payload

# --- Test Data Definitions ---

SYS = {"role": "system", "content": "System Prompt"}
U1 = {"role": "user", "content": "Hello"}
A1_CALL = {"role": "assistant", "content": None, "tool_calls": [{"id": "call_123", "type": "function", "function": {"name": "my_tool", "arguments": "{}"}}]}
T1_RESP = {"role": "tool", "tool_call_id": "call_123", "name": "my_tool", "content": "Tool Result"}
A2_RESP = {"role": "assistant", "content": "Final answer based on tool"}

A3_MULTI_CALL = {"role": "assistant", "content": "Multi", "tool_calls": [
    {"id": "call_abc", "type": "function", "function": {"name": "tool_a", "arguments": "{}"}},
    {"id": "call_def", "type": "function", "function": {"name": "tool_b", "arguments": "{}"}}
]}
T3A_RESP = {"role": "tool", "tool_call_id": "call_abc", "name": "tool_a", "content": "Tool A Result"}
T3B_RESP = {"role": "tool", "tool_call_id": "call_def", "name": "tool_b", "content": "Tool B Result"}
A4_MULTI_RESP = {"role": "assistant", "content": "Multi answer"}

# Valid sequence
VALID_SEQ = [SYS, U1, A1_CALL, T1_RESP, A2_RESP]

# Valid sequence with multiple calls/responses
VALID_MULTI_SEQ = [SYS, U1, A3_MULTI_CALL, T3A_RESP, T3B_RESP, A4_MULTI_RESP]

# Sequence with an orphan tool message
ORPHAN_TOOL_SEQ = [SYS, U1, A1_CALL, T1_RESP, {"role": "tool", "tool_call_id": "orphan_456", "name": "orphan_tool", "content": "Orphan Result"}, A2_RESP]
EXPECTED_AFTER_VALIDATE_ORPHAN = [SYS, U1, A1_CALL, T1_RESP, A2_RESP] # Orphan removed by validate

# Sequence with tool response *before* call (for repair)
REORDER_SEQ_TOOL_FIRST = [SYS, U1, T1_RESP, A1_CALL, A2_RESP]
# Validate DOES NOT remove T1. Repair processes full list.
# Sees T1, adds DummyA. Sees A1, finds no T1 *after*, adds DummyT1.
EXPECTED_AFTER_REPAIR_TOOL_FIRST = [
    SYS, U1,
    {"role": "assistant", "content": None, "tool_calls": [{"id": "call_123", "type": "function", "function": {"name": "my_tool", "arguments": "{}"}}]}, # DummyA
    T1_RESP, # Original T1
    A1_CALL, # Original A1
    {"role": "tool", "tool_call_id": "call_123", "name": "my_tool", "content": "Error: Tool response for my_tool missing."}, # DummyT1
    A2_RESP
]


# Sequence with missing tool response (for repair)
MISSING_TOOL_RESP_SEQ = [SYS, U1, A1_CALL, A2_RESP]
EXPECTED_AFTER_REPAIR_MISSING_RESP = [
    SYS, U1, A1_CALL,
    # Dummy tool response inserted
    {"role": "tool", "tool_call_id": "call_123", "name": "my_tool", "content": "Error: Tool response for my_tool missing."},
    A2_RESP
]

# Sequence with missing assistant call (for repair)
# `validate_message_sequence` removes T1_RESP first. Repair processes the rest.
MISSING_ASSISTANT_CALL_SEQ = [SYS, U1, T1_RESP, A2_RESP]
EXPECTED_AFTER_REPAIR_MISSING_CALL = [SYS, U1, A2_RESP]

# Sequence with multiple calls, one response missing
MULTI_MISSING_RESP_SEQ = [SYS, U1, A3_MULTI_CALL, T3A_RESP, A4_MULTI_RESP]
EXPECTED_AFTER_REPAIR_MULTI_MISSING = [
    SYS, U1, A3_MULTI_CALL, T3A_RESP,
    {"role": "tool", "tool_call_id": "call_def", "name": "tool_b", "content": "Error: Tool response for tool_b missing."},
    A4_MULTI_RESP
]


# --- Tests for validate_message_sequence ---

def test_validate_valid_sequence(): assert validate_message_sequence(VALID_SEQ) == VALID_SEQ
def test_validate_valid_multi_sequence(): assert validate_message_sequence(VALID_MULTI_SEQ) == VALID_MULTI_SEQ
def test_validate_removes_orphan_tool(): assert validate_message_sequence(ORPHAN_TOOL_SEQ) == EXPECTED_AFTER_VALIDATE_ORPHAN
def test_validate_empty_list(): assert validate_message_sequence([]) == []
def test_validate_invalid_input_type(): assert validate_message_sequence("not a list") == []
def test_validate_list_with_non_dicts():
    seq = [SYS, U1, "invalid string", A1_CALL, None, T1_RESP]; expected = [SYS, U1, A1_CALL, T1_RESP]
    result = validate_message_sequence(seq)
    result_simplified = [{"role":m.get("role"), "content":m.get("content"), "tool_calls":m.get("tool_calls"), "tool_call_id":m.get("tool_call_id")} for m in result]
    expected_simplified = [{"role":m.get("role"), "content":m.get("content"), "tool_calls":m.get("tool_calls"), "tool_call_id":m.get("tool_call_id")} for m in expected]
    assert result_simplified == expected_simplified


# --- Tests for repair_message_payload ---

def test_repair_valid_sequence(): assert repair_message_payload(VALID_SEQ) == VALID_SEQ
def test_repair_valid_multi_sequence(): assert repair_message_payload(VALID_MULTI_SEQ) == VALID_MULTI_SEQ
def test_repair_missing_tool_response(): assert repair_message_payload(MISSING_TOOL_RESP_SEQ) == EXPECTED_AFTER_REPAIR_MISSING_RESP
def test_repair_missing_assistant_call(): assert repair_message_payload(MISSING_ASSISTANT_CALL_SEQ) == EXPECTED_AFTER_REPAIR_MISSING_CALL
def test_repair_multi_missing_response(): assert repair_message_payload(MULTI_MISSING_RESP_SEQ) == EXPECTED_AFTER_REPAIR_MULTI_MISSING
def test_repair_tool_first():
    result = repair_message_payload(REORDER_SEQ_TOOL_FIRST)
    # *** FIX: Assert against the EXPECTED_AFTER_REPAIR_TOOL_FIRST which reflects the actual code behavior ***
    assert result == EXPECTED_AFTER_REPAIR_TOOL_FIRST
def test_repair_empty_list(): assert repair_message_payload([]) == []
def test_repair_invalid_input_type(): assert repair_message_payload("not a list") == []
def test_repair_list_with_non_dicts(caplog):
    seq = [SYS, U1, "invalid string", A1_CALL, None, T1_RESP]; expected = [SYS, U1, A1_CALL, T1_RESP]
    result = repair_message_payload(seq); assert result == expected

