# agent_pentest documentation

Start with the [top-level README](../README.md) for the elevator pitch
and quickstart. Detailed docs live here:

| Document | What's inside |
| --- | --- |
| [architecture.md](./architecture.md) | Components, data flow, request lifecycle, sequence diagrams |
| [attacks.md](./attacks.md) | The 7 built-in attack categories, seed format, technique catalogue |
| [judge.md](./judge.md) | Judge contract, JSON schema, heuristic overrides, fallback logic |
| [transports.md](./transports.md) | `kind: openai` vs `kind: ollama`, when to use each |
| [usage.md](./usage.md) | Full CLI + programmatic usage, every flag, every YAML knob |
| [extending.md](./extending.md) | Adding a new attack category in ~10 lines |
| [case-study-guardrail.md](./case-study-guardrail.md) | Real comparison: guarded vs unguarded LLM endpoint |
| [safety.md](./safety.md) | Responsible-use guidance, scope of the tool, what it is *not* |

If you only have time for one doc, read **architecture.md** —
everything else fans out from it.
