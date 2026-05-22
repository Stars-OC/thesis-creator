from pathlib import Path

from scripts.core.package_loader import load_discipline_package
from scripts.core.package_validator import validate_package


def test_business_management_package_is_valid():
    root = Path(__file__).resolve().parents[1]
    result = validate_package(root / "packages" / "disciplines" / "business_management")
    assert result["valid"] is True


def test_law_package_is_valid():
    root = Path(__file__).resolve().parents[1]
    result = validate_package(root / "packages" / "disciplines" / "law")
    assert result["valid"] is True


def test_business_management_does_not_require_code_by_default():
    root = Path(__file__).resolve().parents[1]
    package = load_discipline_package(root, "business_management")
    assert package["writing_rules"]["artifacts"]["code_required"] is False
