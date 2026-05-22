# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .package_loader import deep_merge, load_discipline_package, read_yaml


DEFAULT_THESIS = {
    "discipline": "cs_se",
    "mode": "undergraduate",
}


def _load_workspace_config(workspace: Path) -> Dict[str, Any]:
    config_path = Path(workspace) / ".thesis-config.yaml"
    if not config_path.exists():
        return {}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _load_mode(skill_root: Path, mode: str) -> Dict[str, Any]:
    mode_path = Path(skill_root) / "packages" / "modes" / f"{mode}.yaml"
    mode_data = read_yaml(mode_path)
    if not mode_data:
        raise FileNotFoundError(f"模式配置不存在: {mode_path}")
    return mode_data


def resolve_runtime_config(skill_root: Path, workspace: Path) -> Dict[str, Any]:
    skill_root = Path(skill_root)
    workspace = Path(workspace)
    workspace_config = _load_workspace_config(workspace)
    thesis_config = deep_merge(DEFAULT_THESIS, workspace_config.get("thesis", {}))

    discipline = thesis_config["discipline"]
    mode = thesis_config["mode"]

    package = load_discipline_package(skill_root, discipline)
    mode_config = _load_mode(skill_root, mode)

    runtime_config = {
        "thesis": thesis_config,
        "package": package,
        "mode": mode_config,
        "workspace_config": workspace_config,
    }

    return runtime_config


def write_runtime_config(skill_root: Path, workspace: Path) -> Path:
    runtime_config = resolve_runtime_config(skill_root, workspace)
    output_path = Path(workspace) / ".thesis-runtime-config.yaml"
    output_path.write_text(
        yaml.safe_dump(runtime_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return output_path
