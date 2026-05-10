# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project uses [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-10

Initial public release.

### Added
- **Orchestrator** with bounded asyncio concurrency, multi-turn
  attacker-LLM escalation, and heuristic-vs-judge reconciliation.
- **Seven attack categories**: `prompt_injection`, `jailbreak`,
  `system_prompt_leak`, `pii_leak`, `harmful_content`, `tool_misuse`,
  `insecure_output`. Seed payloads in
  `agent_pentest/seeds/*.yaml`.
- **OpenAI-compatible transport** (`OpenAICompatClient`) and
  **Ollama-native transport** (`OllamaNativeClient`), selectable
  per-endpoint via `kind: openai | ollama`.
- **Tool-call bait** (`delete_all`, `grant_admin`, `send_email`)
  advertised on `tool_misuse` probes so abuse is observable.
- **LLM-as-judge** with strict-JSON contract, lenient parser
  (synonyms, fenced output), and graceful fallback to heuristics.
- **Reporter** producing JSON + Markdown with category summary and
  full transcripts of failed probes. CLI exits with code 2 when any
  category is flagged (CI-gateable).
- **`agent-pentest demo`** subcommand: hermetic, in-process fake
  server that exercises the full pipeline in ~3 seconds with no
  external dependencies.
- **`agent-pentest init-config`** subcommand to scaffold a YAML
  config with sensible defaults.
- **24 unit + integration tests** including fake-server end-to-end
  coverage of the real `openai` SDK path.
- **Documentation tree** under `docs/` covering architecture,
  attacks, judge contract, transports, usage, extending, safety,
  and a guardrail comparison case study.

### Known limitations
- Indicator-token heuristic can fire on refusals that *quote* the
  marker (e.g. "I cannot say PWND-7421"). The orchestrator biases
  toward false positives by design; future work: refusal-phrase
  guard.
- `tool_misuse` probes assume OpenAI-style `tools=[...]` semantics.
  Targets that ignore the bait will be evaluated on text content
  only.
- The Presidio-style detectors used by typical guardrails won't
  match arbitrary defended secrets — see
  [docs/case-study-guardrail.md](docs/case-study-guardrail.md).
