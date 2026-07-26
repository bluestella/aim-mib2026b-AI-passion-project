/**
 * The rules bundle, and the resolution logic that mirrors `daloy.rules_engine`.
 *
 * The bundle is imported rather than fetched: it is a build-time artefact, so
 * bundling it means the app has no loading state, no fetch failure path, and no
 * chance of rendering before its own data arrives. The vanilla version fetched it
 * and needed an error screen for `file://`; that whole class of problem is gone.
 */

import bundle from '@/data/rules.json';
import type {
  Animation,
  Material,
  Override,
  PathwayId,
  Resolution,
  RulesBundle,
  Selection,
} from './types';

/**
 * The single cast from generated JSON to the declared contract.
 *
 * `resolveJsonModule` infers a structural type from the file's current contents,
 * which is not the same as the contract — it would happily infer `string` for a
 * field the Python may emit as null. Casting once here means every consumer is
 * checked against `RulesBundle` instead of against today's data.
 */
export const RULES = bundle as unknown as RulesBundle;

export const MATERIALS: Material[] = RULES.materials;
export const BARANGAYS: string[] = RULES.barangays;

export function findMaterial(materialClass: string): Material | undefined {
  return MATERIALS.find((m) => m.class === materialClass);
}

/**
 * Map a junkshop trade name to a material class.
 *
 * The taxonomy is keyed to trade names on purpose (plan §5.1) — `bote`, `sibak`,
 * `tanso` are what an item is actually called at the counter. Mirrors
 * `RulesEngine.find_by_local_name`.
 */
export function findByLocalName(name: string): Material | undefined {
  const needle = name.trim().toLowerCase();
  return MATERIALS.find(
    (m) =>
      m.class.toLowerCase() === needle ||
      m.local_names.some((alias) => alias.toLowerCase() === needle),
  );
}

/** Display name: trade name first, falling back to the class. */
export function displayName(m: Material): string {
  return m.local_names[0] ?? m.class;
}

/** Secondary line: remaining trade names, or a humanised class. */
export function subName(m: Material): string {
  const rest = m.local_names.slice(1);
  return rest.length > 0 ? rest.join(', ') : m.class.replace(/_/g, ' ');
}

/**
 * What the picker tile shows in place of a price.
 *
 * A nominal price on a material most shops refuse is worse than no price at all:
 * it reads as an invitation to carry the thing across the barangay.
 */
export function priceTag(m: Material): { text: string; hasValue: boolean } {
  if (m.often_refused) return { text: 'Madalas tinatanggihan', hasValue: false };
  if (m.price.has_market) return { text: m.price.display, hasValue: true };
  return { text: 'Walang bumibili', hasValue: false };
}

function overrideMatches(o: Override, selection: Selection): boolean {
  if (o.when.user_flag !== undefined && selection.flags.includes(o.when.user_flag)) {
    return true;
  }
  return o.when.contaminated === true && selection.contaminated;
}

/**
 * Resolve a selection to its disposal pathway.
 *
 * Mirrors `daloy.rules_engine.RulesEngine.resolve`, in the same order: the first
 * matching override wins and replaces both the pathway and the prep text. Keeping
 * the order identical is what stops the two implementations answering differently.
 *
 * Throws on an unknown class rather than rendering a blank card — that can only
 * happen if the bundle and the caller disagree, which is a bug, not a user state.
 */
export function resolve(selection: Selection): Resolution {
  const material = findMaterial(selection.materialClass);
  if (!material) {
    throw new Error(
      `Unknown material class: ${selection.materialClass}. ` +
        `Known: ${MATERIALS.map((m) => m.class).join(', ')}`,
    );
  }

  let pathwayId: PathwayId = material.pathway;
  let animation: Animation = material.animation;
  let override: Override | null = null;

  for (const candidate of RULES.overrides) {
    if (overrideMatches(candidate, selection)) {
      pathwayId = candidate.pathway;
      animation = candidate.animation;
      override = candidate;
      break;
    }
  }

  const pathway = RULES.pathways[pathwayId];
  if (!pathway) {
    throw new Error(`Bundle is missing pathway definition: ${pathwayId}`);
  }

  return {
    material,
    pathway,
    pathwayId,
    animation,
    override,
    prepTl: override?.prep_tl || material.prep_tl,
  };
}

/**
 * Whether the unverified-price caveat should appear.
 *
 * Only caveat a price that is actually on screen: an override suppresses the price,
 * so the caveat would be talking about nothing.
 */
export function showsPriceCaveat(resolution: Resolution): boolean {
  return (
    resolution.override === null &&
    resolution.material.price.has_market &&
    !resolution.material.often_refused &&
    !RULES.verification.phase2_gate_met
  );
}

/** Human-readable label for an override toggle. */
export function overrideLabel(o: Override): string {
  if (o.when.contaminated) return 'May dumi ng pagkain o mantika';
  if (o.when.user_flag === 'battery') return 'Baterya ito';
  if (o.when.user_flag === 'electronic') return 'Electronic / may kable ito';
  return o.id;
}
