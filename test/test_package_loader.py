from pathlib import Path

from scripts.core.package_loader import deep_merge, load_discipline_package


def test_deep_merge_overrides_nested_values():
    base = {"writing": {"a": 1, "b": 2}, "checks": ["base"]}
    override = {"writing": {"b": 3}, "checks": ["discipline"]}
    assert deep_merge(base, override) == {
        "writing": {"a": 1, "b": 3},
        "checks": ["discipline"],
    }


def test_load_discipline_package_inherits_base():
    root = Path(__file__).resolve().parents[1]
    package = load_discipline_package(root, "cs_se")
    assert package["manifest"]["id"] == "cs_se"
    assert package["structure"]["structure"]["chapters"][0]["title"] == "绪论"
    assert package["writing_rules"]["artifacts"]["code_required"] is True
