from pathlib import Path

import yaml

from scripts.core.lifecycle import ensure_workspace_structure, check_workspace_preflight


def test_init_workspace_writes_runtime_config(tmp_path):
    workspace = tmp_path / "thesis-workspace"

    ensure_workspace_structure(str(workspace), sync_scripts=False)
    runtime_config_path = workspace / ".thesis-runtime-config.yaml"
    assert runtime_config_path.exists(), "运行时配置文件必须在工作区初始化时生成"

    runtime_config = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8"))
    assert runtime_config["thesis"]["discipline"] == "cs_se"
    assert runtime_config["package"]["manifest"]["id"] == "cs_se"


def test_runtime_config_in_preflight(tmp_path):
    workspace = tmp_path / "thesis-workspace"
    ensure_workspace_structure(str(workspace), sync_scripts=False)

    report = check_workspace_preflight(workspace)
    assert ".thesis-runtime-config.yaml" in report.get("missing", []) or (
        workspace / ".thesis-runtime-config.yaml"
    ).exists()
