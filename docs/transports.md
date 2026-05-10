# Transports

`agent_pentest` can talk to two wire protocols. Each
`EndpointConfig` (target / attacker / judge) chooses one via the
`kind` field.

## `kind: openai` (default)

- Endpoint: `POST {base_url}/chat/completions`
- Implementation: `OpenAICompatClient` in `agent_pentest/client.py`,
  built on the official `openai` Python SDK.
- Compatible with: OpenAI, Azure OpenAI, vLLM, llama.cpp server,
  LM Studio, OpenRouter, Together, Groq, Anthropic via OpenAI shim,
  Ollama on its `/v1` route, etc.

```yaml
target:
  kind: openai          # default, can be omitted
  base_url: https://api.openai.com/v1
  api_key: sk-...
  model: gpt-4o-mini
```

For Ollama on the OpenAI route:

```yaml
target:
  kind: openai
  base_url: http://localhost:11434/v1
  api_key: ollama       # any non-empty value works
  model: llama3.2:latest
```

## `kind: ollama`

- Endpoint: `POST {base_url}/api/chat`
- Implementation: `OllamaNativeClient`, talks to Ollama's native
  protocol via `httpx`.
- Use this when the target only exposes Ollama-native (notably
  proxies that wrap Ollama, e.g. `guardrail-ollama-proxy`).

```yaml
target:
  kind: ollama
  base_url: http://127.0.0.1:11435   # the proxy
  api_key: ollama
  model: llama3.2:latest
```

The native client normalizes Ollama's response shape to the same
internal `ChatCallResult` that the OpenAI client returns:

- `message.content` → `result.content`
- `message.tool_calls[].function.arguments` → re-serialized as a JSON
  string so heuristics and the judge can treat it identically to the
  OpenAI shape.

## When to mix transports

It's normal to mix them within one config. A common setup:

```yaml
target:
  kind: ollama                          # the thing under test
  base_url: http://127.0.0.1:11435
  model: llama3.2:latest

attacker:
  kind: openai                          # any high-temperature local model
  base_url: http://localhost:11434/v1
  model: qwen2.5:7b
  temperature: 0.9

judge:
  kind: openai                          # same for the judge
  base_url: http://localhost:11434/v1
  model: qwen2.5:7b
  temperature: 0.0
```

## Adding a new transport

Implement the `ChatClient` protocol from `agent_pentest/client.py`:

```python
class ChatClient(Protocol):
    cfg: EndpointConfig
    async def chat(self, messages, *, tools=None,
                   temperature=None, max_tokens=None) -> ChatCallResult: ...
    async def aclose(self) -> None: ...
```

Then register it in `make_client()`. Two existing implementations
(`OpenAICompatClient`, `OllamaNativeClient`) are good templates —
they handle retries, error normalization, and tool-call shape
conversion.

## Limitations

- `tool_misuse` probes assume the target supports OpenAI-style
  `tools=[...]`. Ollama-native targets that don't implement tool
  calling will simply ignore the bait — the probe will be graded on
  text content only.
- The OpenAI client uses `tenacity` to retry only on `APITimeoutError`.
  Other failures bubble up to a recorded `error` on the
  `AttackTurn` and a `Verdict.ERROR` on the result.
