# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

from .package_validator import validate_package


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _load_package_files(package_dir: Path) -> Dict[str, Any]:
    validate_package(package_dir)
    return {
        "manifest": read_yaml(package_dir / "manifest.yaml"),
        "structure": read_yaml(package_dir / "structure.yaml"),
        "writing_rules": read_yaml(package_dir / "writing_rules.yaml"),
        "checklist": read_yaml(package_dir / "checklist.yaml"),
        "diagrams": read_yaml(package_dir / "diagrams.yaml"),
        "package_dir": str(package_dir),
    }


def load_base_package(skill_root: Path) -> Dict[str, Any]:
    return _load_package_files(Path(skill_root) / "packages" / "base")


def load_discipline_package(skill_root: Path, discipline: str) -> Dict[str, Any]:
    skill_root = Path(skill_root)
    discipline_dir = skill_root / "packages" / "disciplines" / discipline
    discipline_package = _load_package_files(discipline_dir)
    parent_id = discipline_package["manifest"].get("extends")

    if parent_id == "base":
        base_package = load_base_package(skill_root)
        return deep_merge(base_package, discipline_package)

    return discipline_package
