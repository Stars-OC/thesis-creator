from pathlib import Path

from scripts.core.package_validator import PackageValidationError, validate_package


def test_validate_package_accepts_complete_base_package():
    root = Path(__file__).resolve().parents[1]
    result = validate_package(root / "packages" / "base")
    assert result["id"] == "base"
    assert result["valid"] is True


def test_validate_package_rejects_missing_required_file(tmp_path):
    package_dir = tmp_path / "broken"
    package_dir.mkdir()
    (package_dir / "manifest.yaml").write_text(
        """
id: broken
name: 损坏模板
version: 1.0.0
extends: base
required_files:
  - structure.yaml
""".strip(),
        encoding="utf-8",
    )

    try:
        validate_package(package_dir)
    except PackageValidationError as exc:
        assert "structure.yaml" in str(exc)
    else:
        raise AssertionError("缺少必填文件时必须报错")
