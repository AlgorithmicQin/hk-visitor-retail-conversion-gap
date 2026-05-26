from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "retail_category_groups.yaml"
BEHAVIORAL_GROUPS = {
    "tourist_sensitive_discretionary",
    "local_daily_consumption",
    "durable_household",
    "residual_other",
}


def load_groups() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)["groups"]


def category_names(group_config: dict) -> list[str]:
    return [item["name"] for item in group_config["categories"]]


def test_required_groups_and_ambiguous_tourist_categories() -> None:
    groups = load_groups()

    assert "tourist_sensitive_discretionary" in groups
    assert "benchmark_total" in groups

    tourist_categories = set(category_names(groups["tourist_sensitive_discretionary"]))
    assert "Medicines and cosmetics" in tourist_categories
    assert "Optical shops" in tourist_categories


def test_total_only_in_benchmark_group() -> None:
    groups = load_groups()

    benchmark_categories = set(category_names(groups["benchmark_total"]))
    behavioral_categories = {
        name
        for group_name in BEHAVIORAL_GROUPS
        for name in category_names(groups[group_name])
    }

    assert "Total" in benchmark_categories
    assert "Total" not in behavioral_categories


def test_no_duplicate_category_names_across_behavioral_groups() -> None:
    groups = load_groups()
    seen = set()
    duplicates = set()

    for group_name in BEHAVIORAL_GROUPS:
        for name in category_names(groups[group_name]):
            if name in seen:
                duplicates.add(name)
            seen.add(name)

    assert not duplicates
