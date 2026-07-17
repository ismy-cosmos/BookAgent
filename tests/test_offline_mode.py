import os

from pipeline.offline_mode import force_offline


def test_sets_both_env_vars_when_unset(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    force_offline()

    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_does_not_override_explicitly_set_values(monkeypatch):
    # setdefault 而不是硬覆盖：调用方（比如部署脚本首次下载模型时需要临时
    # 联网）显式设过的值不应该被这里覆盖掉。
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")

    force_offline()

    assert os.environ["HF_HUB_OFFLINE"] == "0"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "0"
