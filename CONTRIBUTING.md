# Contributing

Thanks for considering a contribution to `agent_pentest`. The main
goal of this project is to be small, readable, and easy to extend
with new attack categories or transports.

## Quick setup

```bash
git clone https://github.com/HoweraProjects/GuardrailStart.git
cd GuardrailStart
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
agent-pentest demo            # hermetic smoke test
```

## Development loop

- Use the bundled hermetic demo (`agent-pentest demo`) as a fast
  smoke test — it's deterministic and runs in ~3 seconds.
- For real-LLM tests, run [`examples/pentest_live.yaml`](examples/pentest_live.yaml)
  against a local Ollama. See [docs/usage.md](docs/usage.md).
- Run `pytest -q` before opening a PR — all tests should pass with
  no internet / no API keys.

## What we welcome

- **New attack categories or techniques.** Check
  [docs/extending.md](docs/extending.md) for the 10-line workflow.
  Cite the public source (paper / repo / blog) for any technique you
  add.
- **New transports.** Anything implementing the `ChatClient`
  protocol can plug in. Templates: `OpenAICompatClient`,
  `OllamaNativeClient`.
- **Sharper heuristics / better refusal-phrase detection** to
  reduce false positives without losing real-evidence overrides.
- **Reporter improvements** — additional formats (HTML, SARIF),
  per-turn timings, severity scoring.
- **Doc clarifications, typo fixes, examples.** Always welcome.

## What we don't accept

- New seed payloads that *only* exist to teach harmful operational
  detail (e.g. step-by-step weapon synthesis with real quantities).
  Seeds should target *probing the safety boundary*, not extending
  the dataset of harmful instructions.
- Code that takes destructive action on observed tool calls (the
  harness is read-only by design).
- Dependencies on closed-source services for required functionality.
  The whole point is "you can run this locally with one Ollama".

## Code style

- Python 3.10+.
- Type hints required on public APIs and any non-trivial function.
- `ruff` config in `pyproject.toml`. Line length 100.
- Async I/O: prefer `asyncio` + `httpx`; avoid blocking calls in
  any orchestrator path.
- Don't add comments that just restate the next line of code; reserve
  comments for non-obvious intent or trade-offs.
- Tests in `tests/`; mock LLM transports via
  `tests/conftest.py::FakeClient`.

## PR checklist

- [ ] `pytest -q` passes locally.
- [ ] `agent-pentest demo` exits with the expected category flags.
- [ ] If you added a new attack category, you also added: seed YAML,
      enum value, registry entry, and at least one unit test.
- [ ] Docs updated when behavior changes.
- [ ] No new mandatory dependencies on hosted services.
- [ ] No real API keys, secrets, or full failure transcripts in the
      commit (see [docs/safety.md](docs/safety.md)).

## Reporting security issues

If you find a real safety issue **in this tool** (e.g. it leaks
credentials, executes attacker-controlled code, etc.), please open
a GitHub security advisory rather than a public issue.

Findings *produced by the tool against your own systems* are not
issues with the tool — they're the intended output. Treat the
reports accordingly (see [docs/safety.md](docs/safety.md)).
