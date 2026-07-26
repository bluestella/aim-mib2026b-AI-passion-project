"""The Stage-2 decision layer: material class -> disposal pathway in Cainta.

Plan §5.2 argues this should be a rules engine rather than a second
classifier, because given the material and the local ordinances the answer is
largely deterministic. This module is that engine.

The one thing it does that a plain dictionary lookup would not: it propagates
*verification state*. Every rule carries the legal source it rests on, and
sources start out `unverified` because the ordinance PDFs have not been read
yet. A resolved pathway therefore knows whether it is safe to present as local
policy, and ``Pathway.is_presentable_as_official`` is what the UI gates on. The
alternative -- rendering a placeholder as though the Sangguniang Bayan said it
-- is exactly the failure mode plan §7.8 exists to prevent.

Usage
-----
    engine = RulesEngine.load()
    card = engine.resolve("PET_bottle")
    card.pathway_id            # -> "sell_junkshop"
    card.is_presentable_as_official  # -> False until the ordinances are harvested
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "rules" / "cainta_disposal_rules.yaml"
)


class UnknownMaterial(KeyError):
    """Raised when a material class is not in the taxonomy."""


@dataclass(frozen=True)
class LegalSource:
    id: str
    citation: str
    title: str
    verification: str
    retrieved_on: str | None = None

    @property
    def verified(self) -> bool:
        return self.verification == "harvested"


@dataclass(frozen=True)
class Price:
    low: float | None
    high: float | None
    confidence: str
    as_of: str | None

    @property
    def has_market(self) -> bool:
        return bool(self.high)

    def display(self) -> str:
        """Render a price range for the Pathway Card, or say plainly there is none."""
        if not self.has_market:
            return "Walang bumibili — no junkshop market"
        if self.low == self.high:
            return f"~PHP {self.low:g}/kg"
        return f"PHP {self.low:g}-{self.high:g}/kg"


@dataclass(frozen=True)
class Pathway:
    """One resolved answer to 'where does this go in Cainta?'."""

    material_class: str
    local_names: list[str]
    pathway_id: str
    label_en: str
    label_tl: str
    terminus: str
    prep_en: str
    prep_tl: str
    price: Price
    citations: list[LegalSource]
    applied_override: str | None = None
    is_critical_class: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def is_presentable_as_official(self) -> bool:
        """True only when every legal source behind this rule has been harvested.

        Until then the app may show the guidance, but must not attribute it to
        the municipality (plan §7.8).
        """
        return bool(self.citations) and all(source.verified for source in self.citations)

    @property
    def leaks_to_waterway(self) -> bool:
        """Whether the wrong choice here ends up in the drainage network.

        Drives the Flow Simulation's leakage branch (plan §2.2).
        """
        return self.terminus in ("disposal", "controlled")


@dataclass
class RulesEngine:
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: Path | str = DEFAULT_RULES_PATH) -> RulesEngine:
        with Path(path).open(encoding="utf-8") as handle:
            return cls(raw=yaml.safe_load(handle))

    # -- lookups ---------------------------------------------------------

    @property
    def material_classes(self) -> list[str]:
        return [row["class"] for row in self.raw.get("materials", [])]

    @property
    def legal_sources(self) -> dict[str, LegalSource]:
        return {
            row["id"]: LegalSource(
                id=row["id"],
                citation=row["citation"],
                title=row.get("title", ""),
                verification=row.get("verification", "unverified"),
                retrieved_on=row.get("retrieved_on"),
            )
            for row in self.raw.get("legal_sources", [])
        }

    def material(self, material_class: str) -> dict[str, Any]:
        for row in self.raw.get("materials", []):
            if row["class"] == material_class:
                return row
        raise UnknownMaterial(
            f"{material_class!r} is not in the taxonomy. Known classes: "
            f"{', '.join(self.material_classes)}"
        )

    def find_by_local_name(self, name: str) -> str | None:
        """Map a junkshop trade name ('bote', 'sibak') to a material class.

        The taxonomy is deliberately keyed to trade names (plan §5.1), so this
        is how a manual material picker in the Phase-3 rules-only build looks
        things up without any model at all.
        """
        needle = name.strip().casefold()
        for row in self.raw.get("materials", []):
            if needle == row["class"].casefold():
                return row["class"]
            if any(needle == str(alias).casefold() for alias in row.get("local_names", [])):
                return row["class"]
        return None

    # -- resolution ------------------------------------------------------

    def resolve(
        self,
        material_class: str,
        *,
        user_flags: set[str] | None = None,
        contaminated: bool = False,
    ) -> Pathway:
        """Resolve a material to its disposal pathway, applying overrides.

        Overrides (battery, e-waste, contamination) cut across material classes
        and are applied after the base lookup, so a contaminated cardboard box
        routes to residual even though cardboard normally sells.
        """
        row = self.material(material_class)
        sources = self.legal_sources
        flags = user_flags or set()

        pathway_id = row["pathway"]
        applied_override = None
        warnings: list[str] = []
        citation_ids = list(row.get("citations", []))

        for override in self.raw.get("overrides", []):
            condition = override.get("when", {})
            matched = (
                condition.get("user_flag") in flags
                or (condition.get("contaminated") and contaminated)
            )
            if not matched:
                continue
            pathway_id = override["pathway"]
            applied_override = override["id"]
            citation_ids = list(override.get("citations", []))
            warnings.append(override["reason_en"])
            break

        pathway_def = self.raw["pathways"][pathway_id]
        price_row = row.get("price_php_per_kg") or {}
        price = Price(
            low=price_row.get("low"),
            high=price_row.get("high"),
            confidence=price_row.get("confidence", "unknown"),
            as_of=price_row.get("as_of"),
        )

        citations = [sources[cid] for cid in citation_ids if cid in sources]
        unverified = [c.citation for c in citations if not c.verified]
        if unverified:
            warnings.append(
                "Legal basis not yet verified against the source document: "
                + "; ".join(unverified)
                + ". Do not attribute this guidance to the municipality."
            )
        if price.has_market and price.confidence == "low":
            warnings.append(
                "Indicative price range only — no verified Cainta shop observations yet."
            )

        return Pathway(
            material_class=row["class"],
            local_names=list(row.get("local_names", [])),
            pathway_id=pathway_id,
            label_en=pathway_def["label_en"],
            label_tl=pathway_def["label_tl"],
            terminus=pathway_def["terminus"],
            prep_en=row.get("prep_en", ""),
            prep_tl=row.get("prep_tl", ""),
            price=price,
            citations=citations,
            applied_override=applied_override,
            is_critical_class=bool(row.get("is_critical_class")),
            warnings=warnings,
        )

    # -- audit -----------------------------------------------------------

    def verification_report(self) -> dict[str, Any]:
        """Summarise how much of the rules table is still provisional.

        This is the Phase-1 gate in plan §9: the rules engine must be able to
        answer 'where does a PET bottle go in Cainta?' *and* cite a document
        that was actually retrieved.
        """
        sources = self.legal_sources.values()
        verified = [s for s in sources if s.verified]
        pending = [s for s in sources if not s.verified]

        priced = [
            row
            for row in self.raw.get("materials", [])
            if (row.get("price_php_per_kg") or {}).get("high")
        ]
        surveyed = self.raw.get("price_provenance", {}).get("verified_shops", 0)

        return {
            "legal_sources_total": len(list(sources)),
            "legal_sources_verified": len(verified),
            "legal_sources_pending": [s.citation for s in pending],
            "materials_total": len(self.material_classes),
            "materials_with_price": len(priced),
            "verified_shops": surveyed,
            "phase1_gate_met": not pending,
            "phase2_gate_met": surveyed >= 25,
        }


def format_pathway_card(pathway: Pathway) -> str:
    """Render a Pathway Card as plain text, for CLI and notebook use.

    The Phase-3 PWA renders the same fields; keeping a text renderer here
    means the rules can be demonstrated before any UI exists.
    """
    names = ", ".join(pathway.local_names)
    lines = [
        f"Ito ay: {pathway.material_class}" + (f" ({names})" if names else ""),
        f"Pathway: {pathway.label_tl} / {pathway.label_en}",
        f"Halaga: {pathway.price.display()}",
        f"Paano: {pathway.prep_tl}",
    ]
    if pathway.is_critical_class:
        lines.append(
            "! Ito ang bumabara sa mga kanal at sapa ng Cainta — walang recycling market."
        )
    if pathway.applied_override:
        lines.append(f"Override applied: {pathway.applied_override}")
    if pathway.citations:
        cites = "; ".join(
            f"{c.citation}{'' if c.verified else ' (unverified)'}" for c in pathway.citations
        )
        lines.append(f"Basehan: {cites}")
    for warning in pathway.warnings:
        lines.append(f"[warning] {warning}")
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Query the Cainta disposal rules.")
    parser.add_argument("material", nargs="?", help="Material class or local trade name.")
    parser.add_argument("--flag", action="append", default=[], help="battery, electronic")
    parser.add_argument("--contaminated", action="store_true")
    parser.add_argument("--audit", action="store_true", help="Print the verification report.")
    args = parser.parse_args()

    engine = RulesEngine.load()

    if args.audit or not args.material:
        report = engine.verification_report()
        print("Rules table verification report")
        print(
            f"  legal sources verified : {report['legal_sources_verified']}"
            f"/{report['legal_sources_total']}"
        )
        for citation in report["legal_sources_pending"]:
            print(f"    pending: {citation}")
        print(f"  materials              : {report['materials_total']}")
        print(f"  verified junkshops     : {report['verified_shops']}")
        print(f"  Phase 1 gate met       : {report['phase1_gate_met']}")
        print(f"  Phase 2 gate met       : {report['phase2_gate_met']}")
        if not args.material:
            print("\nPass a material class or trade name to resolve a pathway, e.g.")
            print("  python -m daloy.rules_engine bote")
            return

    resolved = engine.find_by_local_name(args.material) or args.material
    pathway = engine.resolve(
        resolved, user_flags=set(args.flag), contaminated=args.contaminated
    )
    print()
    print(format_pathway_card(pathway))


if __name__ == "__main__":
    main()
