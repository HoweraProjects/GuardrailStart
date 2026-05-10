"""Tests for the self-contained demo command."""

from __future__ import annotations

import json

import pytest

from agent_pentest.demo import run_demo_async
from agent_pentest.types import AttackCategory


@pytest.mark.asyncio
async def test_demo_vulnerable_flags_multiple_categories(tmp_path):
    json_path, md_path = await run_demo_async(tmp_path, vulnerable=True)
    assert json_path.exists()
    assert md_path.exists()
    report = json.loads(json_path.read_text())

    assert report["total_attacks"] >= 20
    assert report["total_failures"] > 0

    flagged = set(report["flagged_categories"])
    # The vulnerable demo target is engineered to fall for multiple
    # attack families; we only assert representative ones to keep this
    # robust to future seed additions.
    assert AttackCategory.SYSTEM_PROMPT_LEAK.value in flagged
    assert AttackCategory.TOOL_MISUSE.value in flagged
    assert AttackCategory.INSECURE_OUTPUT.value in flagged


@pytest.mark.asyncio
async def test_demo_safe_target_has_no_flags(tmp_path):
    json_path, _ = await run_demo_async(tmp_path, vulnerable=False)
    report = json.loads(json_path.read_text())
    assert report["total_failures"] == 0
    assert report["flagged_categories"] == []
