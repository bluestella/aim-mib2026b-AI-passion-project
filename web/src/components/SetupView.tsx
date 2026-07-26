'use client';

import Link from 'next/link';
import { BARANGAYS } from '@/lib/rules';
import { useStore } from '@/lib/store';

/**
 * The entire location model.
 *
 * There is no geolocation call anywhere in this app. Plan §7.5 required binning a
 * coordinate before storage; with no junkshop locations there is nothing to compute
 * a distance to, so v1 never obtains a coordinate at all and never triggers a
 * permission prompt. Stronger than the rule asked for, and simpler.
 */
export default function SetupView() {
  const { setBarangay } = useStore();

  return (
    <section>
      <h2>Saang barangay kayo?</h2>
      <p className="lede">
        Isang beses lang itatanong. Nananatili ito sa telepono ninyo — hindi ito ipinapadala
        kahit saan.
      </p>

      <div className="grid grid-2">
        {BARANGAYS.map((name) => (
          <button key={name} className="choice" onClick={() => setBarangay(name)}>
            <span className="name">{name}</span>
          </button>
        ))}
      </div>

      <p className="fineprint">
        Hindi namin hinihingi ang eksaktong lokasyon ninyo. Barangay lang.{' '}
        <Link href="/privacy">Bakit?</Link>
      </p>
    </section>
  );
}
