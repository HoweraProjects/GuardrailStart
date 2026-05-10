# GuardrailStart — `agent_pentest`

Automated red-team / pentest harness for **OpenAI-compatible** and
**Ollama-native** LLM endpoints.

A local LLM acts as the **attacker** (mutates seed payloads into
adversarial prompts). Another local LLM acts as the **judge** (grades
each transcript with a strict-JSON verdict). The orchestrator probes
seven categories of LLM-application risk; categories with failures are
**flagged** in a JSON + Markdown report. The CLI exits with code `2`
when anything is flagged, so it drops straight into CI.

```
                            ┌──────────────────────┐
                            │     Orchestrator     │
                            └──────────┬───────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                        ▼
      ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
      │  Attacker    │  craft  │   Target     │ probe   │    Judge     │
      │  local LLM   │ ──────► │  LLM API     │ ◄────── │  local LLM   │
      └──────────────┘         └──────────────┘         └──────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │     Reporter     │
                              │  JSON + Markdown │
                              └──────────────────┘
```

## What it tests

| Category | Examples |
| --- | --- |
| `prompt_injection`    | direct override, indirect-via-data, tool-hijack, translation smuggling |
| `jailbreak`           | DAN persona, hypothetical/roleplay, dual-response, base64-encoded |
| `system_prompt_leak`  | "repeat your hidden instructions", debug pretext, completion priming |
| `pii_leak`            | memorized PII recall, "sample" records, `os.getenv`-style format-string extraction |
| `harmful_content`     | weapons synthesis, working malware, harassment, self-harm |
| `tool_misuse`         | confused-deputy via injected manuals, privilege escalation, parameter smuggling |
| `insecure_output`     | XSS payload emission, raw concatenated SQL, AWS metadata SSRF URLs |

Full catalogue: [`docs/attacks.md`](docs/attacks.md).

## Demo (no API keys, ~3 seconds)

```bash
pip install -e .
agent-pentest demo
```

This spins up an in-process fake OpenAI server that plays attacker,
judge, and a deliberately-vulnerable target — the entire pipeline
runs end-to-end without any external dependency:

```
Pentest results by category
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Category           ┃ Total ┃ Failures ┃ Highest sev ┃ Flagged ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━┩
│ prompt_injection   │     4 │        2 │ high        │   YES   │
│ jailbreak          │     4 │        0 │ -           │   no    │
│ system_prompt_leak │     3 │        3 │ medium      │   YES   │
│ pii_leak           │     3 │        1 │ medium      │   YES   │
│ harmful_content    │     4 │        0 │ -           │   no    │
│ tool_misuse        │     3 │        3 │ critical    │   YES   │
│ insecure_output    │     3 │        3 │ high        │   YES   │
└────────────────────┴───────┴──────────┴─────────────┴─────────┘
Target FLAGGED on: prompt_injection, system_prompt_leak, pii_leak,
                   tool_misuse, insecure_output
JSON report:     pentest_reports/demo/pentest-...json
Markdown report: pentest_reports/demo/pentest-...md
```

For a contrast slide: `agent-pentest demo --safe` produces a clean
"no category flagged" run against a well-behaved target.

## Real run against a local LLM

With Ollama available locally:

```bash
ollama serve &
ollama pull qwen2.5:7b           # attacker / judge
ollama pull llama3.2:latest      # target

agent-pentest init-config pentest.yaml   # edit endpoints / models
agent-pentest run -c pentest.yaml
```

Every run writes:

- `pentest_reports/<run>/pentest-<UTC>.json` — full machine-readable
  transcript of every attacker prompt, target reply, tool call,
  latency, and judge rationale.
- `pentest_reports/<run>/pentest-<UTC>.md` — human-readable summary
  with every failed probe's full transcript.

## Pentesting an Ollama-native target (e.g. a guardrail proxy)

Set `kind: ollama` on the target endpoint:

```yaml
target:
  kind: ollama
  base_url: http://127.0.0.1:11435       # e.g. guardrail-ollama-proxy
  model: llama3.2:latest
attacker:
  kind: openai
  base_url: http://localhost:11434/v1    # raw Ollama
  model: qwen2.5:7b
judge:
  kind: openai
  base_url: http://localhost:11434/v1
  model: qwen2.5:7b
```

A worked example with deltas between guarded vs. unguarded runs lives
in [`docs/case-study-guardrail.md`](docs/case-study-guardrail.md).

## Programmatic API

```python
import asyncio
from agent_pentest import PentestConfig, Orchestrator

async def main():
    cfg = PentestConfig.from_yaml("pentest.yaml")
    orch = Orchestrator(cfg)
    try:
        report = await orch.run()
    finally:
        await orch.aclose()
    for c in report.flagged_categories:
        print("FLAGGED:", c)

asyncio.run(main())
```

## Repo layout

```
agent_pentest/                    # the package
├── orchestrator.py               # async multi-turn attack loop
├── client.py                     # OpenAI + Ollama transports + factory
├── judge.py                      # LLM-as-judge with strict-JSON parsing
├── reporter.py                   # JSON + Markdown reports
├── demo.py                       # in-process fake server for `demo`
├── attacks/                      # attack modules + base class
│   ├── base.py
│   └── registry.py
└── seeds/                        # YAML seed payloads, one per category
    ├── prompt_injection.yaml
    ├── jailbreak.yaml
    ├── system_prompt_leak.yaml
    ├── pii_leak.yaml
    ├── harmful_content.yaml
    ├── tool_misuse.yaml
    └── insecure_output.yaml

docs/                             # full documentation tree
examples/                         # ready-to-run YAML configs
pentest_reports/                  # case-study reports + COMPARISON.md
tests/                            # 24 unit + integration tests
```

## Documentation

| Doc | Topic |
| --- | --- |
| [docs/architecture.md](docs/architecture.md)         | Components, data flow, request lifecycle |
| [docs/attacks.md](docs/attacks.md)                   | Attack categories + seed format |
| [docs/judge.md](docs/judge.md)                       | Judge contract + heuristic overrides |
| [docs/transports.md](docs/transports.md)             | `kind: openai` vs `kind: ollama` |
| [docs/usage.md](docs/usage.md)                       | CLI + programmatic usage |
| [docs/extending.md](docs/extending.md)               | Add a new attack category in 10 lines |
| [docs/case-study-guardrail.md](docs/case-study-guardrail.md) | Real comparison: guarded vs unguarded LLM |
| [docs/safety.md](docs/safety.md)                     | Responsible use, threat model, hygiene |

## Tests

```bash
pip install -e '.[dev]'
pytest -q
```

24 tests, all hermetic — no internet or API keys needed.

## License

MIT — see [LICENSE](LICENSE).

## Responsible use

This is an offensive-security tool. Only point it at systems you own
or are explicitly authorized to test. Treat the report transcripts as
sensitive — they contain successful jailbreak prompts and the
target's actual disallowed outputs. See
[docs/safety.md](docs/safety.md) for the full guidance.
