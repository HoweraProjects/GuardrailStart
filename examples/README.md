# Example configurations

| File | Purpose |
| --- | --- |
| `pentest_live.yaml` | Pentest a hardened, system-prompt-bound `llama3.2:latest` model running on local Ollama (`/v1` route). Useful as a starting point for a real campaign. |
| `pentest_unguarded.yaml` | Baseline: same target as `pentest_guarded.yaml` but bypasses the guardrail proxy. Used in the [guardrail case study](../docs/case-study-guardrail.md). |
| `pentest_guarded.yaml` | Same target model, but routed through `guardrail-ollama-proxy` on `:11435`. Demonstrates `kind: ollama` transport. Used in the case study. |

Run any of them with:

```bash
agent-pentest run -c examples/pentest_live.yaml
```

Edit the `base_url` / `model` / `system_prompt` fields to suit your
target. See [docs/usage.md](../docs/usage.md) for every YAML option.
