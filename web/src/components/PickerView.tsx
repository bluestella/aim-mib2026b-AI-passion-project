'use client';

import { MATERIALS, displayName, priceTag, subName } from '@/lib/rules';

/**
 * The manual material picker — this is what stands in for the classifier in v1.
 *
 * Tiles are labelled with junkshop trade names rather than material classes, because
 * `bote` and `sibak` are what the thing is actually called at the counter. That
 * choice is the whole reason the taxonomy was built the way it was (plan §5.1).
 */
export default function PickerView({
  barangay,
  onPick,
}: {
  barangay: string;
  onPick: (materialClass: string) => void;
}) {
  return (
    <section>
      <h2>Ano ang hawak ninyo?</h2>
      <p className="lede">Pindutin ang pinakamalapit na tugma.</p>

      <div className="grid grid-2">
        {MATERIALS.map((m) => {
          const tag = priceTag(m);
          return (
            <button key={m.class} className="choice" onClick={() => onPick(m.class)}>
              <span className="name">{displayName(m)}</span>
              <span className="sub">{subName(m)}</span>
              <span className={tag.hasValue ? 'tag value' : 'tag none'}>{tag.text}</span>
            </button>
          );
        })}
      </div>

      <p className="fineprint">
        Barangay {barangay}. Ang mga presyo ay tinatayang halaga lamang — magtanong pa rin sa
        junkshop.
      </p>
    </section>
  );
}
