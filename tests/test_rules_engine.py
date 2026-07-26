"""Tests for the Stage-2 decision layer.

These lock down the behaviour the plan actually depends on: the Phase-1 gate
("where does a PET bottle go in Cainta?"), the sachet special case, override
precedence, and -- most importantly -- that provisional rules cannot be
presented as official policy.
"""

from __future__ import annotations

import pytest

from daloy.rules_engine import RulesEngine, UnknownMaterial, format_pathway_card


@pytest.fixture(scope="module")
def engine() -> RulesEngine:
    return RulesEngine.load()


def test_taxonomy_matches_the_plan(engine: RulesEngine) -> None:
    """Plan §5.1: ten material classes plus a residual catch-all."""
    classes = engine.material_classes
    assert len(classes) == 11
    assert "residual_other" in classes
    assert len(set(classes)) == len(classes), "material classes must be unique"


def test_phase1_gate_question(engine: RulesEngine) -> None:
    """The Phase-1 gate in plan §9, stated as a test."""
    pathway = engine.resolve("PET_bottle")
    assert pathway.pathway_id == "sell_junkshop"
    assert pathway.price.has_market
    assert pathway.citations, "a pathway must name the rule it rests on"


def test_sachet_has_no_market_and_is_flagged_critical(engine: RulesEngine) -> None:
    """Plan §5.1: the most important class in the table."""
    pathway = engine.resolve("plastic_film_sachet")
    assert pathway.pathway_id == "residual_to_slf"
    assert not pathway.price.has_market
    assert pathway.is_critical_class
    assert pathway.leaks_to_waterway
    assert "no junkshop market" in pathway.price.display()


def test_organic_routes_to_compost_not_residual(engine: RulesEngine) -> None:
    """RA 9003 treats biodegradables as diverted, not residual."""
    assert engine.resolve("organic_food_waste").pathway_id == "home_compost"


def test_local_trade_names_resolve(engine: RulesEngine) -> None:
    """The taxonomy is keyed to junkshop trade names (plan §5.1)."""
    assert engine.find_by_local_name("bote") == "PET_bottle"
    assert engine.find_by_local_name("sibak") == "HDPE_PP_rigid"
    assert engine.find_by_local_name("tanso") == "copper_wire"
    assert engine.find_by_local_name("karton") == "cardboard"
    assert engine.find_by_local_name("  BOTE  ") == "PET_bottle"
    assert engine.find_by_local_name("not-a-material") is None


def test_contamination_override_beats_the_base_rule(engine: RulesEngine) -> None:
    """A greasy box is refused at the counter, whatever the material says."""
    clean = engine.resolve("cardboard")
    dirty = engine.resolve("cardboard", contaminated=True)
    assert clean.pathway_id == "sell_junkshop"
    assert dirty.pathway_id == "residual_to_slf"
    assert dirty.applied_override == "contaminated-recyclable"


def test_special_waste_flags_route_to_dropoff(engine: RulesEngine) -> None:
    pathway = engine.resolve("ferrous_metal", user_flags={"battery"})
    assert pathway.pathway_id == "special_waste_dropoff"
    assert pathway.applied_override == "special-waste-battery"


def test_unverified_rules_are_not_presentable_as_official(engine: RulesEngine) -> None:
    """Plan §7.8 — the guardrail that matters most before Phase 1 completes.

    Every legal source currently ships as `unverified`, so nothing may be
    attributed to the municipality. When the ordinance harvester flips those to
    `harvested`, this assertion is expected to need updating -- deliberately,
    because that is a decision someone should make consciously in a diff.
    """
    pathway = engine.resolve("PET_bottle")
    assert not pathway.is_presentable_as_official
    assert any("not yet verified" in w for w in pathway.warnings)


def test_every_material_resolves_and_names_a_known_pathway(engine: RulesEngine) -> None:
    known = set(engine.raw["pathways"])
    for material_class in engine.material_classes:
        pathway = engine.resolve(material_class)
        assert pathway.pathway_id in known
        assert pathway.label_tl and pathway.label_en


def test_every_citation_resolves_to_a_declared_source(engine: RulesEngine) -> None:
    """A dangling citation id would silently drop a rule's legal basis."""
    declared = set(engine.legal_sources)
    for row in engine.raw["materials"]:
        assert set(row.get("citations", [])) <= declared, row["class"]
    for override in engine.raw["overrides"]:
        assert set(override.get("citations", [])) <= declared, override["id"]


def test_unknown_material_raises_with_a_useful_message(engine: RulesEngine) -> None:
    with pytest.raises(UnknownMaterial) as excinfo:
        engine.resolve("styrofoam")
    assert "PET_bottle" in str(excinfo.value)


def test_verification_report_reflects_provisional_state(engine: RulesEngine) -> None:
    report = engine.verification_report()
    assert report["phase1_gate_met"] is False, "no ordinance PDF has been harvested yet"
    assert report["phase2_gate_met"] is False, "no junkshops surveyed yet"
    assert report["materials_total"] == 11


def test_pathway_card_renders_bilingually(engine: RulesEngine) -> None:
    card = format_pathway_card(engine.resolve("plastic_film_sachet"))
    assert "Ito ay:" in card
    assert "Cainta" in card
    assert "[warning]" in card
