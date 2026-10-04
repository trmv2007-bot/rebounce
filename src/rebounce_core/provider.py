from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol

from .models import ModelMessage, ModelResponse, ModelStreamChunk


class ModelProviderError(RuntimeError):
    """Raised when a model provider cannot complete a request."""


class ModelProvider(Protocol):
    """Provider-neutral interface used by the companion runtime."""

    @property
    def name(self) -> str:
        ...

    async def generate(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        ...

    def stream(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:
        ...


class StubModelProvider:
    """Deterministic provider used for tests and a dependency-free smoke path."""

    @property
    def name(self) -> str:
        return "stub"

    async def generate(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        del messages
        return ModelResponse(
            content="[Stage 1] Companion runtime is connected; Stage 0 foundation remains intact.",
            model_name=model or "stub",
            provider_name=self.name,
        )

    async def _stream_impl(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:
        response = await self.generate(messages, model=model)
        for part in response.content.split(" "):
            yield ModelStreamChunk(
                content=part + " ",
                model_name=response.model_name,
                provider_name=response.provider_name,
            )
            await asyncio.sleep(0)

    def stream(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:
        return self._stream_impl(messages, model=model)


class OpenAICompatibleProvider:
    """Provider for local or remote OpenAI-compatible /v1/chat/completions APIs.

    This uses only Python's standard library, so local llama.cpp-compatible
    servers and other OpenAI-compatible endpoints can be used without adding
    a model SDK to the ReBounce core.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        base_url = base_url.rstrip("/")
        self.base_url = base_url
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.default_model = default_model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "openai-compatible"

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _build_request(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None,
        stream: bool,
    ) -> urllib.request.Request:
        selected_model = model or self.default_model
        if not selected_model:
            raise ValueError("model must be supplied when no default_model is configured")
        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": [{"role": message.role.value, "content": message.content} for message in messages],
            "stream": stream,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return urllib.request.Request(
            self.chat_completions_url,
            data=data,
            headers=headers,
            method="POST",
        )

    @staticmethod
    def _provider_error(exc: Exception) -> ModelProviderError:
        if isinstance(exc, urllib.error.HTTPError):
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            detail = body[:500] or str(exc.reason)
            return ModelProviderError(f"provider HTTP {exc.code}: {detail}")
        if isinstance(exc, urllib.error.URLError):
            return ModelProviderError(f"provider connection failed: {exc.reason}")
        return ModelProviderError(str(exc))

    async def generate(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> ModelResponse:
        request = self._build_request(messages, model=model, stream=False)
        try:
            response = await asyncio.to_thread(urllib.request.urlopen, request, self.timeout)
            try:
                payload = json.loads(response.read().decode("utf-8"))
            finally:
                response.close()
        except Exception as exc:
            raise self._provider_error(exc) from exc

        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"] or ""
            selected_model = str(payload.get("model") or model or self.default_model)
            finish_reason = str(choice.get("finish_reason") or "stop")
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelProviderError("provider returned an invalid chat-completions payload") from exc

        return ModelResponse(
            content=content,
            model_name=selected_model,
            provider_name=self.name,
            finish_reason=finish_reason,
        )

    async def _stream_impl(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:
        request = self._build_request(messages, model=model, stream=True)
        try:
            response = await asyncio.to_thread(urllib.request.urlopen, request, self.timeout)
        except Exception as exc:
            raise self._provider_error(exc) from exc

        selected_model = model or self.default_model or "unknown"
        try:
            while True:
                raw_line = await asyncio.to_thread(response.readline)
                if not raw_line:
                    break
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if data == "[DONE]":
                    break

                try:
                    payload = json.loads(data)
                    selected_model = str(payload.get("model") or selected_model)
                    choice = payload["choices"][0]
                    delta = choice.get("delta") or {}
                    content = delta.get("content") or ""
                    finish_reason = choice.get("finish_reason")
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise ModelProviderError("provider returned invalid streaming data") from exc

                if content or finish_reason:
                    yield ModelStreamChunk(
                        content=str(content),
                        model_name=selected_model,
                        provider_name=self.name,
                        finish_reason=str(finish_reason) if finish_reason else None,
                    )
        except Exception as exc:
            if isinstance(exc, ModelProviderError):
                raise
            raise self._provider_error(exc) from exc
        finally:
            response.close()

    def stream(
        self,
        messages: Sequence[ModelMessage],
        *,
        model: str | None = None,
    ) -> AsyncIterator[ModelStreamChunk]:
        return self._stream_impl(messages, model=model)
