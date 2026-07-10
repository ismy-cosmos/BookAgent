from pipeline.api import agent_registry


def test_evict_client_removes_cached_entry(monkeypatch):
    agent_registry.reset_registry()
    monkeypatch.setattr(agent_registry, "_clients", {"old-id": object()})

    agent_registry.evict_client("old-id")

    assert "old-id" not in agent_registry._clients


def test_evict_client_noop_when_not_cached():
    agent_registry.reset_registry()
    agent_registry.evict_client("never-cached")  # 不报错
