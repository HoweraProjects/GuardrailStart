"""Unit tests for the LLM-as-judge."""

from __future__ import annotations

import pytest

from agent_pentest.client import ChatCallResult
from agent_pentest.judge import Judge, _parse_judge_json
from agent_pentest.types import AttackCategory, AttackTurn, Verdict

from .conftest import FakeClient


def test_parse_strict_json():
    op = _parse_judge_json('{"verdict": "fail", "confidence": 0.91, "rationale": "leaked"}')
    assert op is not None
    assert op.verdict == Verdict.FAIL
    assert 0.9 <= op.confidence <= 1.0


def test_parse_with_codefence_and_extra_text():
    raw = "```json\n{\"verdict\": \"pass\", \"confidence\": 0.7, \"rationale\": \"refused\"}\n```"
    op = _parse_judge_json(raw)
    assert op is not None
    assert op.verdict == Verdict.PASS


def test_parse_synonyms():
    op = _parse_judge_json('{"verdict": "broken", "confidence": 1, "rationale": "x"}')
    assert op.verdict == Verdict.FAIL


def test_parse_garbage_returns_none():
    assert _parse_judge_json("totally not json") is None


@pytest.mark.asyncio
async def test_judge_uses_llm_response():
    def respond(messages, ctx):
        return ChatCallResult(
            content='{"verdict": "fail", "confidence": 0.95, "rationale": "compromised"}',
            latency_ms=1,
        )

    judge = Judge(FakeClient(respond))
    turns = [AttackTurn(attacker_prompt="a", target_response="PWND-7421")]
    op = await judge.evaluate(
        category=AttackCategory.PROMPT_INJECTION,
        goal="break it",
        turns=turns,
        expected_tool_misuse=None,
        heuristic=Verdict.INCONCLUSIVE,
    )
    assert op.verdict == Verdict.FAIL
    assert op.confidence > 0.9


@pytest.mark.asyncio
async def test_judge_falls_back_on_error():
    def respond(messages, ctx):
        return ChatCallResult(error="boom", latency_ms=1)

    judge = Judge(FakeClient(respond))
    turns = [AttackTurn(attacker_prompt="a", target_response="ok")]
    op = await judge.evaluate(
        category=AttackCategory.JAILBREAK,
        goal="g",
        turns=turns,
        expected_tool_misuse=None,
        heuristic=Verdict.PASS,
    )
    assert op.verdict == Verdict.PASS
    assert "Judge unavailable" in op.rationale


@pytest.mark.asyncio
async def test_judge_falls_back_on_unparseable():
    def respond(messages, ctx):
        return ChatCallResult(content="I think it's fine actually", latency_ms=1)

    judge = Judge(FakeClient(respond))
    turns = [AttackTurn(attacker_prompt="a", target_response="ok")]
    op = await judge.evaluate(
        category=AttackCategory.JAILBREAK,
        goal="g",
        turns=turns,
        expected_tool_misuse=None,
        heuristic=Verdict.INCONCLUSIVE,
    )
    assert op.verdict == Verdict.INCONCLUSIVE
    assert "non-JSON" in op.rationale
