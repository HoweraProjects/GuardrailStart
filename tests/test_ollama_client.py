"""Tests for the Ollama-native client + factory."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agent_pentest.client import OllamaNativeClient, OpenAICompatClient, make_client
from agent_pentest.config import EndpointConfig
from agent_pentest.types import Message


class _FakeOllamaHandler(BaseHTTPRequestHandler):
    last_body: dict | None = None

    def log_message(self, *_):
        return

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        type(self).last_body = body
        last = body["messages"][-1]
        # Echo behavior: if the last user message asks to invoke a tool,
        # produce a synthetic tool call. Otherwise produce content.
        msg: dict = {"role": "assistant", "content": ""}
        if "TOOL_CALL_TEST" in last.get("content", ""):
            msg["tool_calls"] = [{
                "function": {"name": "delete_all", "arguments": {}},
            }]
        else:
            msg["content"] = f"echo: {last.get('content', '')}"
        resp = {
            "model": body.get("model", ""),
            "message": msg,
            "done": True,
            "done_reason": "stop",
        }
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def fake_ollama():
    server = HTTPServer(("127.0.0.1", 0), _FakeOllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()


def test_factory_dispatches_on_kind():
    cfg_oai = EndpointConfig(kind="openai", model="x", base_url="http://localhost/v1")
    cfg_oll = EndpointConfig(kind="ollama", model="x", base_url="http://localhost")
    assert isinstance(make_client(cfg_oai), OpenAICompatClient)
    assert isinstance(make_client(cfg_oll), OllamaNativeClient)


@pytest.mark.asyncio
async def test_ollama_client_basic_content(fake_ollama):
    client = OllamaNativeClient(EndpointConfig(
        kind="ollama", model="m", base_url=fake_ollama,
    ))
    try:
        result = await client.chat([Message(role="user", content="hello")])
    finally:
        await client.aclose()
    assert result.ok
    assert result.content == "echo: hello"
    body = _FakeOllamaHandler.last_body
    assert body["stream"] is False
    assert body["model"] == "m"
    assert body["messages"][-1]["content"] == "hello"


@pytest.mark.asyncio
async def test_ollama_client_normalizes_tool_calls(fake_ollama):
    client = OllamaNativeClient(EndpointConfig(
        kind="ollama", model="m", base_url=fake_ollama,
    ))
    try:
        result = await client.chat(
            [Message(role="user", content="please TOOL_CALL_TEST now")],
            tools=[{"type": "function", "function": {"name": "delete_all",
                                                       "parameters": {"type": "object",
                                                                       "properties": {}}}}],
        )
    finally:
        await client.aclose()
    assert result.ok
    assert result.tool_calls and len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc["function"]["name"] == "delete_all"
    # arguments are normalized to a JSON string for parity with OpenAI.
    assert isinstance(tc["function"]["arguments"], str)


@pytest.mark.asyncio
async def test_ollama_client_handles_http_error():
    # Point at a closed port to force a connection error.
    client = OllamaNativeClient(EndpointConfig(
        kind="ollama", model="m", base_url="http://127.0.0.1:1",
        timeout_s=2.0,
    ))
    try:
        result = await client.chat([Message(role="user", content="x")])
    finally:
        await client.aclose()
    assert not result.ok
    assert result.error
