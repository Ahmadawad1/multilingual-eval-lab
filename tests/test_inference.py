import json

import httpx
import pytest

from backend.inference import complete, inference_status, settings


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "http://example.com",
        "http://127.0.0.1.evil/",
        "http://user:secret@127.0.0.1",
        "http://127.0.0.1?key=secret",
        "file:///tmp/model",
        "http://192.168.1.1",
    ],
)
def test_reject_remote_or_credential_urls(monkeypatch, url):
    monkeypatch.setenv("LOCAL_LLM_URL", url)
    with pytest.raises(ValueError):
        settings()


@pytest.mark.parametrize("provider", ["ollama", "openai"])
def test_local_adapters_record_config_and_identity(monkeypatch, provider):
    monkeypatch.setenv("LOCAL_LLM_PROVIDER", provider)
    monkeypatch.setenv("LOCAL_LLM_MODEL", "test-model")
    monkeypatch.setenv(
        "LOCAL_LLM_URL", "http://localhost:1234" + ("/v1" if provider == "openai" else "")
    )
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "models": [{"name": "test-model", "digest": "abc"}],
                    "data": [{"id": "test-model"}],
                },
            )
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "message": {"content": "hello"},
                "choices": [{"message": {"content": "hello"}}],
            },
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        "backend.inference.httpx.Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    assert inference_status()["model_available"] is True
    result = complete("test system", {"question": "مرحبا"}, json_mode=True)
    assert result["raw"] == "hello"
    assert result["config"]["seed"] == 42
    assert result["model_identity"]["id"] == "test-model"
    body = json.loads(requests[-1].content)
    assert body["stream"] is False
    assert requests[-1].url.host == "127.0.0.1"
    assert result["request"] == body


def test_connection_failure_is_optional(monkeypatch):
    monkeypatch.setattr(
        "backend.inference.model_inventory",
        lambda _: (_ for _ in ()).throw(httpx.ConnectError("not running")),
    )
    assert inference_status()["connected"] is False


@pytest.mark.parametrize("response_body", [{}, {"message": {}}, {"message": {"content": ""}}])
def test_malformed_chat_responses_are_actionable(monkeypatch, response_body):
    monkeypatch.setenv("LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("LOCAL_LLM_MODEL", "test-model")
    monkeypatch.setattr("backend.inference.model_inventory", lambda _: [{"id": "test-model"}])
    real_client = httpx.Client
    monkeypatch.setattr(
        "backend.inference.httpx.Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response_body)), **kw
        ),
    )
    with pytest.raises(ValueError, match="malformed|empty"):
        complete("test", {"question": "hello"})
    # The semaphore must be released even after a provider error.
    with pytest.raises(ValueError, match="malformed|empty"):
        complete("test", {"question": "again"})
