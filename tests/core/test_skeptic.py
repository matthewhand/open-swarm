"""Skeptic role: retry on failure, stop on success, bounded N, no nag."""

import pytest

from swarm.core.classifier_verdict import SKEPTIC_VERDICT_TOOL, submit_skeptic_verdict
from swarm.core.skeptic import (
    SKEPTIC_INSTRUCTIONS,
    SKEPTIC_MAX_RETRIES,
    parse_skeptic_verdict,
    run_with_skeptic,
    skeptic_from_team,
)


def test_parse_skeptic_verdict_yes_no():
    yes = parse_skeptic_verdict("YES")
    assert yes.accomplished is True
    assert yes.findings == ""
    no = parse_skeptic_verdict("NO\nMissing decision.md")
    assert no.accomplished is False
    assert "decision.md" in no.findings
    structured = parse_skeptic_verdict({"accomplished": True})
    assert structured.accomplished is True
    blank = parse_skeptic_verdict("   \n   \n")
    assert blank.accomplished is False
    # First line whitespace-only after a non-empty remainder (ZWSP + blank).
    weird = parse_skeptic_verdict("\u200b   \nNO\nmissing file")
    assert weird.accomplished is False
    assert "missing file" in weird.findings or "NO" in weird.findings


@pytest.mark.asyncio
async def test_unwired_skeptic_runs_once():
    calls: list[str] = []

    def run_fn(_agent, prompt: str) -> str:
        calls.append(prompt)
        return "done"

    result = await run_with_skeptic(
        agent=object(),
        prompt="Write summary.md",
        skeptic=None,
        run_fn=run_fn,
    )
    assert calls == ["Write summary.md"]
    assert result.attempts == 1
    assert result.retries == 0
    assert result.accomplished is None
    assert result.nagged is False
    assert result.output == "done"


@pytest.mark.asyncio
async def test_success_does_not_retry_or_nag():
    runs: list[str] = []
    reviews: list[tuple[str, str]] = []

    def run_fn(_agent, prompt: str) -> str:
        runs.append(prompt)
        return "summary.md written"

    def review_fn(_skeptic, prompt: str, output: str):
        reviews.append((prompt, output))
        return "YES"

    result = await run_with_skeptic(
        agent="original",
        prompt="Write summary.md from notes",
        skeptic="skeptic",
        run_fn=run_fn,
        review_fn=review_fn,
    )
    assert runs == ["Write summary.md from notes"]
    assert len(reviews) == 1
    assert reviews[0][0] == "Write summary.md from notes"
    assert result.retries == 0
    assert result.accomplished is True
    assert result.nagged is False
    assert result.findings == []


@pytest.mark.asyncio
async def test_failure_hands_findings_back_and_retries():
    runs: list[str] = []

    def run_fn(_agent, prompt: str) -> str:
        runs.append(prompt)
        if "Skeptic findings" in prompt:
            return "summary.md now includes the missing section"
        return "I talked about it but wrote nothing"

    reviews = iter(["NO\nNo summary.md on disk", "YES"])

    def review_fn(_skeptic, _prompt: str, _output: str) -> str:
        return next(reviews)

    result = await run_with_skeptic(
        agent="original",
        prompt="Write summary.md from notes",
        skeptic="skeptic",
        run_fn=run_fn,
        review_fn=review_fn,
    )
    assert len(runs) == 2
    assert runs[0] == "Write summary.md from notes"
    assert "Skeptic findings" in runs[1]
    assert "No summary.md on disk" in runs[1]
    assert result.retries == 1
    assert result.accomplished is True
    assert result.nagged is False
    assert result.findings[0].startswith("No summary.md")


@pytest.mark.asyncio
async def test_retries_are_bounded_to_two():
    runs = 0

    def run_fn(_agent, _prompt: str) -> str:
        nonlocal runs
        runs += 1
        return "still incomplete"

    def review_fn(_skeptic, _prompt: str, _output: str) -> str:
        return "NO\nstill missing the file"

    result = await run_with_skeptic(
        agent="original",
        prompt="Ship the feature",
        skeptic="skeptic",
        max_retries=SKEPTIC_MAX_RETRIES,
        run_fn=run_fn,
        review_fn=review_fn,
    )
    # 1 original + 2 retries; never an infinite loop.
    assert runs == 1 + SKEPTIC_MAX_RETRIES
    assert SKEPTIC_MAX_RETRIES == 2
    assert result.retries == 2
    assert result.accomplished is False
    assert result.nagged is False


def test_skeptic_instructions_name_verdict_tool():
    assert SKEPTIC_VERDICT_TOOL in SKEPTIC_INSTRUCTIONS
    assert "MUST call" in SKEPTIC_INSTRUCTIONS


@pytest.mark.asyncio
async def test_invoke_fn_prose_fail_closes_not_parsed_as_pass():
    def invoke(_agent, _prompt: str) -> str:
        return "YES\nEverything looks accomplished."

    result = await run_with_skeptic(
        agent="original",
        prompt="Write summary.md",
        skeptic="skeptic",
        max_retries=0,
        run_fn=lambda _a, _p: "summary.md written",
        invoke_fn=invoke,
    )
    assert result.accomplished is False
    assert any(SKEPTIC_VERDICT_TOOL in item for item in result.findings)


@pytest.mark.asyncio
async def test_invoke_fn_verdict_tool_pass_stops():
    def invoke(_agent, _prompt: str) -> str:
        submit_skeptic_verdict(verdict="pass", reason="file on disk")
        return "ignored prose"

    result = await run_with_skeptic(
        agent="original",
        prompt="Write summary.md",
        skeptic="skeptic",
        run_fn=lambda _a, _p: "summary.md written",
        invoke_fn=invoke,
    )
    assert result.accomplished is True
    assert result.retries == 0
    assert result.nagged is False


def test_skeptic_from_team_unwired():
    assert skeptic_from_team([{"name": "Writer", "role": "default"}]) is None
    team = [
        {"name": "Writer", "role": "default"},
        {"name": "Critic", "role": "skeptic"},
    ]
    assert skeptic_from_team(team)["name"] == "Critic"
