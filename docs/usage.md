# Usage

## CLI

After `pip install -e .` you have one entry point with three
subcommands:

```
agent-pentest <command> [options]

  demo          Self-contained demo against an in-process fake target.
  init-config   Write an example pentest.yaml.
  run           Run a campaign defined by a YAML config.
```

### `agent-pentest demo`

Hermetic, no external dependencies, ~3 seconds.

```bash
agent-pentest demo                          # vulnerable target
agent-pentest demo --safe                   # well-behaved target
agent-pentest demo -o ./out/demo            # custom output dir
```

The demo spins up an in-process HTTP server that plays attacker,
judge, and target roles. It produces real JSON + Markdown reports.
See [architecture.md](./architecture.md#components) for what's wired
to what.

### `agent-pentest init-config`

```bash
agent-pentest init-config pentest.yaml
```

Writes a fully-commented example config. Refuses to overwrite an
existing file.

### `agent-pentest run`

```bash
agent-pentest run -c pentest.yaml
agent-pentest run -c pentest.yaml \
    --category jailbreak --category tool_misuse
agent-pentest run -c pentest.yaml \
    --attempts 4 --max-turns 5 --concurrency 8 \
    -o ./pentest_reports/release-candidate-42
```

Flags:

| Flag | Effect |
| --- | --- |
| `-c, --config PATH` | Required. Path to YAML config. |
| `--category NAME` | Restrict run to one category (repeatable). |
| `-o, --output-dir PATH` | Override `output_dir` from the config. |
| `--concurrency N` | Override the asyncio semaphore size. |
| `--attempts N` | Override `attempts_per_technique`. |
| `--max-turns N` | Override the multi-turn escalation depth. |

**Exit codes:**

- `0` — every category passed.
- `2` — at least one category was flagged. Wire this into CI to
  gate releases.

## YAML config

```yaml
target:
  kind: openai                       # 'openai' (default) or 'ollama'
  name: target-under-test            # free-form label
  base_url: http://localhost:11434/v1
  api_key: ollama
  model: llama3.2:latest
  temperature: 0.2
  max_tokens: 1024
  timeout_s: 60.0
  extra_headers: {}
  system_prompt: |                   # optional; injected as role=system
    You are SupportBot for AcmeCorp. Refuse anything ...

attacker:
  kind: openai
  base_url: http://localhost:11434/v1
  api_key: ollama
  model: qwen2.5:7b
  temperature: 0.9                   # high temp = more variety
  max_tokens: 384
  timeout_s: 120.0

judge:
  kind: openai
  base_url: http://localhost:11434/v1
  api_key: ollama
  model: qwen2.5:7b
  temperature: 0.0                   # deterministic JSON
  max_tokens: 256
  timeout_s: 120.0

# --- run shape ---
categories:                          # leave empty = all 7
  - prompt_injection
  - jailbreak
  - system_prompt_leak
  - pii_leak
  - harmful_content
  - tool_misuse
  - insecure_output
attempts_per_technique: 2            # # of variants per (technique)
max_turns: 3                         # multi-turn escalation depth
concurrency: 4                       # asyncio Semaphore
flag_threshold: 1                    # # failures within a cat to flag it
output_dir: ./pentest_reports
seed: 1337                           # RNG seed
```

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

    print(f"flagged: {report.flagged_categories}")
    for r in report.results:
        if r.succeeded:
            print(f"  {r.attack_id}: {r.judge.rationale}")

asyncio.run(main())
```

You can inject your own clients (e.g. for testing or to use a
non-HTTP transport):

```python
from agent_pentest.orchestrator import Orchestrator
orch = Orchestrator(
    cfg,
    target_client=my_target_client,
    attacker_client=my_attacker_client,
    judge_client=my_judge_client,
)
```

Any object satisfying the `ChatClient` protocol works
([transports.md](./transports.md)).

## Reports

After every run, `output_dir` contains:

- `pentest-<UTC-timestamp>.json` — full machine-readable report
  (`PentestReport.model_dump_json`). Includes every attacker prompt,
  target reply, tool call, latency, and judge rationale.
- `pentest-<UTC-timestamp>.md` — human-readable summary with a
  category table and full transcripts of failed probes.

Pipe the JSON into your security dashboard, or commit the Markdown
into your release notes.
