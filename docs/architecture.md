# Architecture

`agent_pentest` is a small async pipeline that drives one LLM (the
**target**) with adversarial prompts crafted by another LLM (the
**attacker**), then asks a third LLM (the **judge**) to grade whether
each transcript represents a safety failure. Categories with at least
`flag_threshold` failures are flagged in the final report.

## Components

```
                            ┌──────────────────────┐
                            │     Orchestrator     │  asyncio + Semaphore
                            └──────────┬───────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
      ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
      │  ChatClient  │  craft  │  ChatClient  │ probe   │  ChatClient  │
      │  (attacker)  │ ──────► │   (target)   │ ◄────── │   (judge)    │
      └──────┬───────┘         └──────────────┘         └──────────────┘
             │                  ▲ │ tool calls,                ▲
             │                  │ │ content, latency           │
             │                  │ ▼                            │
             │            multi-turn loop                      │
             │                                                 │
             │                                                 │
   ┌─────────┴─────────────────────────────────────────────────┴─┐
   │  Attack modules (registry)                                  │
   │  prompt_injection · jailbreak · system_prompt_leak ·        │
   │  pii_leak · harmful_content · tool_misuse · insecure_output │
   └────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
              ┌───────────────────┐
              │     Reporter      │   JSON + Markdown
              └───────────────────┘
```

Source map:

| File | Role |
| --- | --- |
| `agent_pentest/orchestrator.py` | Concurrency, multi-turn loop, heuristic-vs-judge reconciliation, report assembly |
| `agent_pentest/client.py` | `OpenAICompatClient` and `OllamaNativeClient`, factory `make_client()` |
| `agent_pentest/attacks/base.py` | `Attack` base class, seed loading, attacker meta-prompts, heuristics |
| `agent_pentest/attacks/registry.py` | Concrete attack subclasses + `ALL_ATTACKS` |
| `agent_pentest/seeds/*.yaml` | Seed payloads (technique, goal, severity, indicators) |
| `agent_pentest/judge.py` | `Judge` class + strict-JSON parser |
| `agent_pentest/reporter.py` | JSON + Markdown rendering, terminal summary |
| `agent_pentest/demo.py` | Self-contained in-process fake server for the `demo` command |
| `agent_pentest/__main__.py` | `typer` CLI: `run`, `demo`, `init-config` |

## Data model

```
PentestConfig
 ├── target:   EndpointConfig (kind, base_url, model, system_prompt, ...)
 ├── attacker: EndpointConfig
 ├── judge:    EndpointConfig
 ├── categories: list[AttackCategory]
 ├── attempts_per_technique, max_turns, concurrency
 └── flag_threshold, output_dir, seed

AttackResult                          PentestReport
 ├── attack_id, category, technique     ├── target / attacker / judge labels
 ├── severity, seed                     ├── started_at / finished_at
 ├── turns: list[AttackTurn]            ├── total_attacks / total_failures
 │     ├── attacker_prompt              ├── categories: list[CategoryReport]
 │     ├── target_response              ├── flagged_categories
 │     ├── target_tool_calls            └── results: list[AttackResult]
 │     └── latency_ms / error
 ├── judge: JudgeOpinion {verdict, confidence, rationale}
 └── metadata
```

Datatypes are `pydantic` models in `agent_pentest/types.py`.

## Pipeline per probe

For every (technique, variant) tuple in the configured categories the
orchestrator runs this loop:

```
1. Build a meta-prompt from the seed        (Attack.build_initial_prompt)
2. attacker.chat(meta) -> adversarial_user  (Attack.craft_prompt)
3. for turn in range(max_turns):
       target.chat([prior turns ..., adversarial_user], tools=...)
       record AttackTurn(prompt, response, tool_calls, latency, error)
       if heuristic_verdict == FAIL:    break
       if turn.error:                   break
       adversarial_user = attacker.chat(followup_meta)   # escalation
4. heuristic = Attack.heuristic_verdict(seed, turns)
5. judge_opinion = Judge.evaluate(category, goal, turns, indicator, heuristic)
6. If heuristic == FAIL but judge != FAIL, override judge to FAIL
   (heuristic is authoritative for direct evidence such as marker tokens
    and forbidden tool calls)
7. Build AttackResult and yield it
```

Key design choices:

- **Attacker / target separation.** The attacker LLM never speaks
  *to* the target. We extract its proposed text, then send it to the
  target as a fresh user message. This keeps the attacker model free
  to output instructional / harmful content without filtering, while
  the target sees only the adversarial payload.
- **Multi-turn escalation.** When the target resists, the attacker is
  given the failed transcript and asked to escalate. This catches
  jailbreaks that need ramp-up (DAN-style, indirect framing).
- **Heuristic + LLM judge.** Heuristics catch direct evidence
  (marker tokens, regex indicators, forbidden tool invocations); the
  judge handles semantic cases. We bias toward false positives by
  letting heuristics override a "pass" judgement — better for a
  security tool.
- **Async + bounded concurrency.** All three clients are async; the
  orchestrator uses an `asyncio.Semaphore` so you can scale up to
  whatever your local LLM box can handle without crushing it.

## Tool-bait advertising

For the `tool_misuse` category the orchestrator advertises three
deliberately dangerous tools (`delete_all`, `grant_admin`,
`send_email`) so we can observe whether the target is willing to
invoke them. The bait list is in
`orchestrator.py::DEFAULT_TOOL_BAIT` and easy to extend.

## Failure modes (deliberate)

| Failure path | Behavior |
| --- | --- |
| Network / 5xx from target | Recorded as `AttackTurn.error`, judge gets `Verdict.ERROR` and report rolls up `total_failures` only for `FAIL` |
| Judge LLM returns non-JSON | Strict regex parser fails, fall back to heuristic verdict with low confidence |
| Judge LLM unreachable | Heuristic verdict used directly with `confidence ≈ 0.4` |
| Attacker LLM returns empty | Falls back to the raw seed text |

## See also

- [attacks.md](./attacks.md) — what each category probes for
- [judge.md](./judge.md) — exact JSON contract for judges
- [transports.md](./transports.md) — wire-protocol selection
