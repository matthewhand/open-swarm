"""Tests for the reusable consensus service (swarm.core.consensus)."""

from __future__ import annotations

import sys

from swarm.core.cli_adapter import CliAdapter, CliResult
from swarm.core.consensus import (
    most_corroborated,
    run_consensus,
    safe_json,
    synthesize,
)

PY = sys.executable


def _r(name: str, text: str, ok: bool = True) -> CliResult:
    return CliResult(name=name, ok=ok, text=text)


def _echo(name: str) -> CliAdapter:
    return CliAdapter.from_config(
        name, {"cmd": [PY, "-c", f"import sys; print('{name}:' + sys.argv[1])", "{prompt}"]}
    )


# --- synthesis: consensus-first, not longest ------------------------------- #

def test_most_corroborated_prefers_agreement_over_length():
    a = _r("a", "use create index concurrently to avoid write locks")
    b = _r("b", "avoid write locks with create index concurrently")  # agrees with a
    c = _r("c", "completely unrelated verbose tangent " * 20)        # the longest, an outlier
    pick = most_corroborated([a, b, c])
    assert pick in (a.text, b.text)  # the corroborated pair...
    assert pick != c.text            # ...NOT the longest answer


def test_most_corroborated_single_survivor_wins():
    assert most_corroborated([_r("a", "only one")]) == "only one"


def test_most_corroborated_no_survivors():
    assert most_corroborated([_r("a", "x", ok=False)]) == ""


def test_synthesize_prefers_judge_answer():
    out = synthesize({"answer": "JUDGED"}, [_r("a", "short"), _r("b", "a much longer answer here")])
    assert out == "JUDGED"


def test_synthesize_without_judge_uses_corroborated():
    a = _r("a", "alpha beta gamma")
    b = _r("b", "alpha beta delta")
    c = _r("c", "zzz " * 40)
    assert synthesize(None, [a, b, c]) in (a.text, b.text)


def test_safe_json_tolerates_prose():
    assert safe_json('here:\n{"answer": "x"}\nthanks') == {"answer": "x"}
    assert safe_json("no json") is None


# --- run_consensus (real subprocesses) ------------------------------------- #

async def test_run_consensus_with_judge():
    judge = CliAdapter.from_config(
        "j", {"cmd": [PY, "-c", "print('{\"answer\": \"JUDGED\", \"done\": true}')", "{prompt}"]}
    )
    res = await run_consensus("q", [_echo("a"), _echo("b")], judge)
    assert res.ok and res.answer == "JUDGED"
    assert len(res.results) == 2 and len(res.ok_results) == 2


async def test_run_consensus_no_judge_uses_corroborated_survivor():
    res = await run_consensus("hi", [_echo("a"), _echo("b")], None)
    assert res.ok and res.answer in ("a:hi", "b:hi")


async def test_run_consensus_drops_failures_and_uses_survivor():
    boom = CliAdapter.from_config("boom", {"cmd": [PY, "-c", "import sys; sys.exit(1)", "{prompt}"]})
    res = await run_consensus("hi", [boom, _echo("good")], None)
    assert res.ok and res.answer == "good:hi"
    assert any(not r.ok for r in res.results)  # the failure is still reported


async def test_run_consensus_all_fail_is_not_ok():
    boom = CliAdapter.from_config("boom", {"cmd": [PY, "-c", "import sys; sys.exit(1)", "{prompt}"]})
    res = await run_consensus("q", [boom], None)
    assert not res.ok and res.answer == ""
