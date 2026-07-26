'use client';

import { RULES, displayName, findMaterial, overrideLabel } from '@/lib/rules';
import type { Override, Selection } from '@/lib/types';

/**
 * The cross-cutting conditions: contamination, batteries, e-waste.
 *
 * Driven entirely by `RULES.overrides`, so adding one to the YAML surfaces it here
 * without touching this file.
 *
 * Checkbox state is derived from `selection` on every render rather than held
 * locally. The vanilla build kept it locally and desynced when the user navigated
 * back from the card: the boxes reset while the flags persisted, showing a verdict
 * the visible controls did not explain.
 */
export default function ModifiersView({
  selection,
  onChange,
  onContinue,
  onBack,
}: {
  selection: Selection;
  onChange: (next: Selection) => void;
  onContinue: () => void;
  onBack: () => void;
}) {
  const material = findMaterial(selection.materialClass);

  function isChecked(o: Override): boolean {
    if (o.when.contaminated) return selection.contaminated;
    return o.when.user_flag !== undefined && selection.flags.includes(o.when.user_flag);
  }

  function toggle(o: Override, checked: boolean): void {
    if (o.when.contaminated) {
      onChange({ ...selection, contaminated: checked });
      return;
    }
    const flag = o.when.user_flag;
    if (flag === undefined) return;
    onChange({
      ...selection,
      flags: checked
        ? [...selection.flags, flag]
        : selection.flags.filter((f) => f !== flag),
    });
  }

  return (
    <section>
      <h2>{material ? displayName(material) : selection.materialClass}</h2>
      <p className="lede">May nagbabago ba sa mga ito?</p>

      <div className="stack">
        {RULES.overrides.map((o) => (
          <label key={o.id} className="toggle">
            <input
              type="checkbox"
              checked={isChecked(o)}
              onChange={(e) => toggle(o, e.target.checked)}
            />
            <div>
              <div className="t-name">{overrideLabel(o)}</div>
              <div className="t-sub">{o.reason_tl}</div>
            </div>
          </label>
        ))}
      </div>

      <button className="primary wide" style={{ marginTop: 16 }} onClick={onContinue}>
        Ituloy
      </button>
      <button className="linkish wide" onClick={onBack}>
        Ibang materyal
      </button>
    </section>
  );
}
