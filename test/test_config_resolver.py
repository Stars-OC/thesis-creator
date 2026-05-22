from pathlib import Path

import yaml

from scripts.core.config_resolver import resolve_runtime_config


def test_resolve_runtime_config_defaults_to_cs_undergraduate(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "thesis-workspace"
    workspace.mkdir()

    result = resolve_runtime_config(root, workspace)

    assert result["thesis"]["discipline"] == "cs_se"
    assert result["thesis"]["mode"] == "undergraduate"
    assert result["package"]["manifest"]["id"] == "cs_se"
    assert result["mode"]["defaults"]["reference_count"] == [20, 30]


def test_resolve_runtime_config_reads_workspace_config(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "thesis-workspace"
    workspace.mkdir()
    (workspace / ".thesis-config.yaml").write_text(
        yaml.safe_dump({"thesis": {"discipline": "cs_se", "mode": "master"}}, allow_unicode=True),
        encoding="utf-8",
    )

    result = resolve_runtime_config(root, workspace)

    assert result["thesis"]["mode"] == "master"
    assert result["mode"]["defaults"]["reference_count"] == [50, 80]
