# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


class PackageValidationError(ValueError):
    pass


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise PackageValidationError(f"YAML 解析失败: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackageValidationError(f"YAML 顶层必须是对象: {path}")
    return data


def validate_package(package_dir: Path) -> Dict[str, Any]:
    package_dir = Path(package_dir)
    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise PackageValidationError(f"缺少 manifest.yaml: {package_dir}")

    manifest = _read_yaml(manifest_path)
    package_id = str(manifest.get("id") or "").strip()
    if not package_id:
        raise PackageValidationError(f"manifest.yaml 缺少 id: {manifest_path}")

    required_files = manifest.get("required_files", [])
    if not isinstance(required_files, list):
        raise PackageValidationError("required_files 必须是列表")

    missing = []
    for relative_path in required_files:
        if not (package_dir / str(relative_path)).exists():
            missing.append(str(relative_path))
    if missing:
        raise PackageValidationError(f"模板包 {package_id} 缺少必填文件: {', '.join(missing)}")

    return {
        "id": package_id,
        "valid": True,
        "manifest": manifest,
        "package_dir": str(package_dir),
    }
