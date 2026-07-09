"""DeepSeek API Client — OpenAI-compatible interface via urllib (zero extra deps)

Provides a llama_cpp-compatible interface so existing code works without changes.
Supports streaming (SSE) and non-streaming chat completions.
"""

import json
import ssl
import urllib.request

from app.core.config import settings


class DeepSeekClient:
    """Mimics llama_cpp.Llama interface using DeepSeek API."""

    def __init__(self, model=None, api_key=None, base_url=None):
        self.model = model or settings.DEEPSEEK_MODEL
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = (base_url or settings.DEEPSEEK_API_BASE).rstrip("/")
        self._ctx = ssl.create_default_context()

    def _http_post(self, path, body, stream=False):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "text/event-stream" if stream else "application/json",
            },
            method="POST",
        )
        return urllib.request.urlopen(req, context=self._ctx, timeout=120)

    def create_chat_completion(self, messages, temperature=0.7, max_tokens=2048,
                               stream=False, response_format=None):
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if response_format:
            body["response_format"] = response_format

        if stream:
            return self._stream_chat(body)
        else:
            return self._sync_chat(body)

    def _sync_chat(self, body):
        resp = self._http_post("/v1/chat/completions", body, stream=False)
        raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        choice = data["choices"][0]
        return {
            "choices": [{
                "message": {
                    "content": choice["message"]["content"] or "",
                    "role": choice["message"].get("role", "assistant"),
                },
                "finish_reason": choice.get("finish_reason", "stop"),
            }],
            "usage": data.get("usage", {}),
        }

    def _stream_chat(self, body):
        """Streaming chat completion using byte-level buffering."""

        class StreamGenerator:
            def __init__(self, http_resp):
                self._resp = http_resp
                self._buf = b""

            def __iter__(self):
                return self

            def __next__(self):
                while True:
                    if b"\n" not in self._buf:
                        try:
                            chunk = self._resp.read(4096)
                        except Exception:
                            chunk = b""
                        if not chunk:
                            raise StopIteration
                        self._buf += chunk

                    idx = self._buf.find(b"\n")
                    if idx == -1:
                        continue
                    raw_line = self._buf[:idx]
                    self._buf = self._buf[idx + 1:]

                    try:
                        line = raw_line.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        continue

                    if not line:
                        continue
                    if line == "data: [DONE]":
                        raise StopIteration
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                return {
                                    "choices": [{
                                        "delta": {"content": content}
                                    }]
                                }
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        resp = self._http_post("/v1/chat/completions", body, stream=True)
        return StreamGenerator(resp)


_client = None


def get_deepseek_client():
    global _client
    if _client is None:
        _client = DeepSeekClient()
        print(f"[DeepSeek] Client initialized: model={_client.model}, base={_client.base_url}")
    return _client
