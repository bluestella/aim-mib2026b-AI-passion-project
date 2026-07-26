"""Tests for the PWA data bundle (plan Phase 3).

Two jobs. First, catch drift: the committed ``app/data/rules.json`` must match a
fresh build, or a rules change silently fails to reach users. Second, assert the
invariants the app depends on — above all that nothing provisional is marked
presentable as official policy.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_app_data import OUTPUT_PATH, REPO_ROOT, build, serialise  # noqa: E402


@pytest.fixture(scope="module")
def bundle() -> dict:
    return build()


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def test_committed_bundle_is_in_sync(bundle: dict) -> None:
    """The check the build script runs in --check mode, as a test."""
    assert OUTPUT_PATH.read_text(encoding="utf-8") == serialise(bundle), (
        "app/data/rules.json is stale. Run: python scripts/build_app_data.py"
    )


def test_check_mode_exits_zero_when_in_sync() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_app_data.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_material_reaches_the_app(bundle: dict) -> None:
    assert len(bundle["materials"]) == 11
    classes = {m["class"] for m in bundle["materials"]}
    assert "plastic_film_sachet" in classes
    assert "residual_other" in classes


def test_nothing_is_presentable_as_official_yet(bundle: dict) -> None:
    """Plan §7.8 — the guardrail, carried across the Python/JS boundary.

    Expected to need updating once the ordinances are harvested. That should be a
    conscious change in a diff, not a silent drift.
    """
    assert bundle["verification"]["phase1_gate_met"] is False
    assert not any(m["presentable_as_official"] for m in bundle["materials"])


def test_every_material_has_a_flow_animation(bundle: dict) -> None:
    """A missing animation key would throw in the browser at render time."""
    for m in bundle["materials"]:
        assert m["animation"] in ("leakage", "recovery"), m["class"]


def test_residual_leaks_and_recyclables_recover(bundle: dict) -> None:
    by_class = {m["class"]: m for m in bundle["materials"]}
    assert by_class["plastic_film_sachet"]["animation"] == "leakage"
    assert by_class["residual_other"]["animation"] == "leakage"
    assert by_class["PET_bottle"]["animation"] == "recovery"
    assert by_class["organic_food_waste"]["animation"] == "recovery"


def test_sachet_carries_no_price_and_is_flagged(bundle: dict) -> None:
    sachet = next(m for m in bundle["materials"] if m["class"] == "plastic_film_sachet")
    assert sachet["is_critical_class"] is True
    assert sachet["price"]["has_market"] is False


def test_every_material_has_tagalog_guidance(bundle: dict) -> None:
    """The app is Tagalog-first; an empty prep_tl renders a blank card section."""
    for m in bundle["materials"]:
        assert m["prep_tl"].strip(), m["class"]


def test_local_trade_names_present_for_the_picker(bundle: dict) -> None:
    """The picker labels every tile with local_names[0]."""
    for m in bundle["materials"]:
        assert m["local_names"], m["class"]


def test_overrides_reach_the_app_with_their_conditions(bundle: dict) -> None:
    ids = {o["id"] for o in bundle["overrides"]}
    assert {"special-waste-battery", "special-waste-ewaste", "contaminated-recyclable"} <= ids
    for o in bundle["overrides"]:
        assert o["when"], o["id"]
        assert o["reason_tl"].strip(), o["id"]


def test_flow_is_labelled_schematic(bundle: dict) -> None:
    """The app must never present the flow diagram as surveyed geometry."""
    assert bundle["flow"]["kind"] == "schematic"
    assert bundle["flow"]["verification"] == "unverified"
    assert bundle["flow"]["caveat"].strip()


def test_flow_paths_terminate(bundle: dict) -> None:
    for key in ("leakage", "recovery"):
        stages = bundle["flow"][key]["stages"]
        assert stages
        assert stages[-1].get("terminal") is True, key


def test_leakage_path_ends_at_laguna_de_bay(bundle: dict) -> None:
    assert bundle["flow"]["leakage"]["stages"][-1]["id"] == "laguna"


def test_no_named_creek_is_asserted(bundle: dict) -> None:
    """Which creek serves which barangay is unverified — the UI must not name one."""
    creek = next(s for s in bundle["flow"]["leakage"]["stages"] if s["id"] == "creek")
    assert creek.get("verification") == "unverified"


def test_all_seven_barangays_offered(bundle: dict) -> None:
    assert len(bundle["barangays"]) == 7
    assert "Santo Niño" in bundle["barangays"]


def test_bundle_is_json_serialisable_without_python_types(committed: dict) -> None:
    """A stray date or tuple would serialise oddly or break json.loads in strict mode."""
    assert isinstance(committed["updated_on"], str)
    assert isinstance(committed["schema_version"], int)


def test_overrides_carry_replacement_prep_text(bundle: dict) -> None:
    """An override changes the pathway, so it must also replace the prep text.

    Otherwise a contaminated PET bottle shows a residual verdict above guidance
    telling the user to rinse it and sell it.
    """
    for o in bundle["overrides"]:
        assert o["prep_tl"].strip(), o["id"]
        assert o["prep_en"].strip(), o["id"]


def test_often_refused_material_is_flagged(bundle: dict) -> None:
    """Glass carries a nominal price but most shops refuse it.

    The picker must not show a green price tag on a material that will send
    someone across the barangay for a refusal.
    """
    glass = next(m for m in bundle["materials"] if m["class"] == "glass_bottle")
    assert glass["often_refused"] is True

    # Nothing with a real, reliable market should be flagged.
    for cls in ("PET_bottle", "aluminium_can", "copper_wire"):
        m = next(x for x in bundle["materials"] if x["class"] == cls)
        assert m["often_refused"] is False, cls
