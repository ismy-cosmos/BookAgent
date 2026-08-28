from pipeline.api import agent_registry


def test_evict_client_removes_cached_entry(monkeypatch):
    agent_registry.reset_registry()
    monkeypatch.setattr(agent_registry, "_clients", {"old-id": object()})

    agent_registry.evict_client("old-id")

    assert "old-id" not in agent_registry._clients


def test_evict_client_noop_when_not_cached():
    agent_registry.reset_registry()
    agent_registry.evict_client("never-cached")  # 不报错


def test_get_model_name_returns_current_model(monkeypatch):
    monkeypatch.setattr(agent_registry, "_MODEL", "custom-model:latest")
    assert agent_registry.get_model_name() == "custom-model:latest"


def test_get_client_uses_openai_endpoint_derived_from_native_ollama_base(monkeypatch):
    agent_registry.reset_registry()
    monkeypatch.setattr(agent_registry, "OLLAMA_BASE_URL", "http://ollama.internal:11434/")
    monkeypatch.setattr(agent_registry, "_get_embedder", lambda: object())
    monkeypatch.setattr(agent_registry, "get_store", lambda _path: object())

    created = []

    def fake_client(**kwargs):
        created.append(kwargs)
        return object()

    monkeypatch.setattr(agent_registry, "OllamaAgentClient", fake_client)

    agent_registry.get_client("book")

    assert created[0]["model"] == agent_registry.get_model_name()
    assert created[0]["base_url"] == "http://ollama.internal:11434/v1"
    agent_registry.reset_registry()
