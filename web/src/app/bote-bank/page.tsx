'use client';

import { MATERIALS, displayName, findMaterial } from '@/lib/rules';
import { useStore } from '@/lib/store';

/**
 * The Bote Bank ledger.
 *
 * Totals mass, not pesos. Every price in the app is an unverified estimate, so a
 * running peso figure would be a made-up number presented back to the user as an
 * achievement — the most persuasive possible way to launder a guess (plan §10).
 */
export default function BoteBankPage() {
  const { bank, hydrated, removeFromBank, clearBank } = useStore();

  if (!hydrated) return <div className="skeleton" aria-busy="true" />;

  const entries = Object.entries(bank).filter(([, n]) => n > 0);
  const items = entries.reduce((sum, [, n]) => sum + n, 0);

  const grams = entries.reduce((sum, [cls, n]) => {
    const m = findMaterial(cls);
    return sum + (m?.typical_unit_mass_g ?? 0) * n;
  }, 0);

  const weight = grams >= 1000 ? `${(grams / 1000).toFixed(1)} kg` : `${Math.round(grams)} g`;

  const sorted = [...entries].sort((a, b) => b[1] - a[1]);

  return (
    <section>
      <h2>Bote Bank</h2>
      <p className="lede">Ang naipon ninyo. Nasa telepono lang ito.</p>

      <div className="totals">
        <div className="total">
          <div className="t-num">{items}</div>
          <div className="t-lab">piraso na naitabi</div>
        </div>
        <div className="total">
          <div className="t-num">{weight}</div>
          <div className="t-lab">tinatayang bigat</div>
        </div>
      </div>

      {sorted.length === 0 ? (
        <div className="empty">
          <strong>Wala pa rito.</strong>
          <div>Mag-scan, tapos pindutin ang &ldquo;Idagdag sa Bote Bank&rdquo;.</div>
        </div>
      ) : (
        <ul className="ledger">
          {sorted.map(([cls, n]) => {
            const m = MATERIALS.find((x) => x.class === cls);
            return (
              <li key={cls}>
                <span className="l-name">{m ? displayName(m) : cls}</span>
                <span className="l-count">{n}</span>
                <button
                  className="l-drop"
                  onClick={() => removeFromBank(cls)}
                  aria-label={`Bawasan ang ${m ? displayName(m) : cls}`}
                >
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <p className="fineprint">
        Tinatayang bigat lamang, batay sa karaniwang timbang bawat piraso. Hindi namin
        ipinapakita ang halaga sa piso dahil wala pang na-verify na presyo.
      </p>

      {sorted.length > 0 && (
        <button className="linkish wide" onClick={clearBank}>
          Burahin lahat
        </button>
      )}
    </section>
  );
}
