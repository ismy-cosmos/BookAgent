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
