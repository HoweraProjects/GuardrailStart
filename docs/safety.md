# Safety / responsible use

## Scope

`agent_pentest` is an offensive-security tool intended for **internal,
authorized evaluation** of LLM-based systems you own or have written
permission to test.

The seed payloads in `agent_pentest/seeds/` deliberately include
patterns from the public LLM-redteam literature: prompt injections,
jailbreak personas, requests for malware / weapons / self-harm
methodology, PII recall, XSS / SQLi / SSRF templates, and
agent-action coercion. The local attacker LLM step is designed to
*amplify* these patterns into novel variants.

This is not a chatbot. It produces adversarial content as a matter
of course. Treat report artifacts (especially the Markdown reports
with full transcripts of failed probes) as sensitive — they may
contain successful jailbreak prompts and the target's actual
disallowed outputs.

## Acceptable use

- Pre-deployment red-teaming of your own LLM features.
- CI gating: the CLI exits with code 2 on any flagged category — fail
  the build if the gate trips.
- Comparative evaluation of models or guardrail layers (see the
  [guardrail case study](./case-study-guardrail.md)).
- Research on defensive techniques.

## Not acceptable

- Pointing the tool at a third-party API without explicit, written
  authorization from the API operator.
- Republishing successful failure transcripts verbatim — they are
  effectively jailbreak corpus contributions.
- Combining this tool with downstream automation that takes real
  destructive actions on observed tool calls (e.g. don't wire
  `tool_misuse::confused_deputy` failures into a pipeline that
  actually deletes data).

## Operator hygiene

When running against a real target:

- Use a dedicated, **non-production** API key.
- Rate-limit (`concurrency`) below the target's quota.
- Tag requests with a clear `extra_headers` value (e.g.
  `X-Pentest-Run: agent-pentest-2026-05-10-T123`) so on-call can
  distinguish them from organic traffic.
- Treat the JSON report as confidential. The transcripts contain
  whatever the target actually leaked.

## Known categories of harm

Even with good operator hygiene, this tool can:

1. **Generate disallowed content via the attacker LLM** — the
   attacker model is asked to compose adversarial prompts; some
   open-weight models will comply broadly. That output never reaches
   real users (it goes to the target), but it is recorded in the
   report.
2. **Trigger real side effects on the target.** If the target is an
   agent with tools wired to real systems, a `tool_misuse::*` probe
   can cause the target to *actually* call those tools. Always test
   against staging environments with mocked tools, never production.
3. **Surface real PII or secrets memorized by the target.** Treat
   reports accordingly.

## Threat-model assumptions

- We assume an authorized internal red-team with shell access to a
  local machine running both the harness and the attacker / judge
  LLMs.
- We do not assume the target obeys any specific protocol beyond
  OpenAI Chat Completions or Ollama-native `/api/chat`.
- We do not protect against attacker-LLM adversarial behavior — if
  you point the attacker role at an untrusted model, that model can
  emit arbitrary text into your reports.

If your threat model differs from these assumptions, audit the
seed YAMLs and the meta-prompts in `attacks/base.py` and `judge.py`
before using.
