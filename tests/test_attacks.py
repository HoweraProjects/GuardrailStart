"""Unit tests for attack modules and seed loading."""

from __future__ import annotations

from agent_pentest.attacks import ALL_ATTACKS, get_attack
from agent_pentest.attacks.base import Seed, _strip_fences
from agent_pentest.types import AttackCategory, AttackTurn, Severity, Verdict


def test_all_categories_have_seeds():
    for cat in AttackCategory:
        attack = get_attack(cat)
        assert attack.seeds, f"{cat} has no seeds"
        for s in attack.seeds:
            assert s.technique
            assert s.goal
            assert s.seed
            assert isinstance(s.severity, Severity)


def test_registry_covers_all_categories():
    assert set(ALL_ATTACKS.keys()) == set(AttackCategory)


def test_strip_fences_unwraps_code_blocks():
    assert _strip_fences("```\nhello\n```") == "hello"
    assert _strip_fences("```python\nx=1\n```") == "x=1"
    assert _strip_fences("plain") == "plain"


def test_heuristic_detects_indicator_token():
    attack = get_attack(AttackCategory.PROMPT_INJECTION)
    seed = Seed(
        technique="t", goal="g", seed="s",
        success_indicators=["PWND-7421"],
    )
    turns = [AttackTurn(attacker_prompt="x", target_response="output: PWND-7421 here")]
    assert attack.heuristic_verdict(seed, turns) == Verdict.FAIL


def test_heuristic_detects_forbidden_tool_call():
    attack = get_attack(AttackCategory.TOOL_MISUSE)
    seed = Seed(
        technique="t", goal="g", seed="s",
        expected_tool_misuse="delete_all",
    )
    turns = [
        AttackTurn(
            attacker_prompt="x",
            target_response="",
            target_tool_calls=[{"function": {"name": "delete_all", "arguments": "{}"}}],
        )
    ]
    assert attack.heuristic_verdict(seed, turns) == Verdict.FAIL


def test_heuristic_inconclusive_otherwise():
    attack = get_attack(AttackCategory.JAILBREAK)
    seed = Seed(technique="t", goal="g", seed="s")
    turns = [AttackTurn(attacker_prompt="x", target_response="I cannot help with that.")]
    assert attack.heuristic_verdict(seed, turns) == Verdict.INCONCLUSIVE
