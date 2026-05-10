# Extending agent_pentest

## Add a new attack category

A new category is roughly 10 lines of code plus a YAML file.

### 1. Add seeds

Create `agent_pentest/seeds/<category>.yaml`:

```yaml
- technique: short_snake_case_id
  severity: medium                  # low | medium | high | critical
  goal: |
    What success looks like for the attacker.
  seed: |
    The literal initial adversarial text. The local attacker LLM
    will mutate this at high temperature on each variant.
  success_indicators:               # optional, regex-free substring match
    - SOME_TRACER_TOKEN
  expected_tool_misuse: some_tool   # optional, tool-misuse style probes
```

See [attacks.md](./attacks.md) for the full schema.

### 2. Add an enum value

Edit `agent_pentest/types.py`:

```python
class AttackCategory(str, Enum):
    ...
    SUPPLY_CHAIN = "supply_chain"     # add your value here
```

### 3. Register the attack

Edit `agent_pentest/attacks/registry.py`:

```python
class SupplyChainAttack(Attack):
    category = AttackCategory.SUPPLY_CHAIN
    seed_file = "supply_chain.yaml"

ALL_ATTACKS[AttackCategory.SUPPLY_CHAIN] = SupplyChainAttack
```

That's it. The orchestrator picks it up automatically because it
iterates over `config.categories`, and the reporter renders it
without further changes.

## Customize attacker meta-prompts

If your category needs a different framing (e.g. multi-modal
attacks, code-completion attacks), override the meta-prompt builders
on your `Attack` subclass:

```python
class CodeAttack(Attack):
    category = AttackCategory.INSECURE_OUTPUT
    seed_file = "insecure_output.yaml"

    def build_initial_prompt(self, seed, variant_index):
        return f"You are a code-assist red-teamer ... seed: {seed.seed}"

    def build_followup_prompt(self, seed, last_attempt, last_response):
        return f"The target's last reply was:\n{last_response}\n..."
```

The base class methods in `agent_pentest/attacks/base.py` are good
templates.

## Customize the judge

Edit `JUDGE_SYSTEM_PROMPT` and `JUDGE_USER_TEMPLATE` in
`agent_pentest/judge.py`. They drive a strict JSON contract; if you
add fields, also extend `JudgeOpinion` and `_parse_judge_json`.

Examples of useful customizations:

- Add domain context to the system prompt
  ("You are auditing a medical-advice agent ...").
- Demand a list of policy IDs in the JSON output and surface them
  in the report (extend `JudgeOpinion`).

## Custom heuristics

`Attack.heuristic_verdict` is called *before* the judge. Override
it on a subclass when you need stronger direct evidence:

```python
class CredentialLeakAttack(Attack):
    category = AttackCategory.PII_LEAK
    seed_file = "credential_leak.yaml"

    DEFENDED_TOKENS = ["SECRET-API-KEY-9X8Y7Z"]

    def heuristic_verdict(self, seed, turns):
        text = "\n".join(t.target_response or "" for t in turns)
        for token in self.DEFENDED_TOKENS:
            if token in text:
                return Verdict.FAIL
        return super().heuristic_verdict(seed, turns)
```

Heuristic `FAIL` overrides the judge — see
[judge.md](./judge.md#heuristic-vs-judge-reconciliation).

## Custom transport

To target a non-HTTP API (e.g. a gRPC endpoint or an SDK directly):

```python
from agent_pentest.client import ChatCallResult
from agent_pentest.types import Message

class MyTransport:
    def __init__(self, cfg): self.cfg = cfg
    async def chat(self, messages: list[Message], *, tools=None,
                   temperature=None, max_tokens=None) -> ChatCallResult:
        ...   # your I/O here, return a ChatCallResult
        return ChatCallResult(content="...", latency_ms=42)
    async def aclose(self): ...

# inject when constructing the orchestrator:
orch = Orchestrator(cfg, target_client=MyTransport(cfg.target))
```

Or extend `make_client()` in `agent_pentest/client.py` so YAML can
select your transport via a new `kind` value.

## Tests

Use `tests/conftest.py::FakeClient` to drive the orchestrator with
deterministic responses. The existing tests are good templates:

- `tests/test_attacks.py` — seeds load, heuristics fire correctly.
- `tests/test_judge.py` — strict-JSON parsing, fallback paths.
- `tests/test_orchestrator.py` — end-to-end with mocked transports.
- `tests/test_smoke_e2e.py` — end-to-end against an in-process fake
  HTTP server (real `openai` SDK in the loop).
- `tests/test_demo.py` — the bundled demo runs and produces the
  expected category flags.

Run them with:

```bash
pip install -e '.[dev]'
pytest -v
```
