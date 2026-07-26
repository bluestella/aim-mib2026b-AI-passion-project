'use client';

import { useState } from 'react';
import { displayName, showsPriceCaveat, subName } from '@/lib/rules';
import { useStore } from '@/lib/store';
import type { Material, Resolution } from '@/lib/types';

/**
 * The Pathway Card — the payload that makes this Cainta-specific rather than a
 * generic recycling lookup (plan §2.1).
 */
export default function PathwayCard({
  resolution,
  onFlow,
  onBack,
  onAgain,
}: {
  resolution: Resolution;
  onFlow: () => void;
  onBack: () => void;
  onAgain: () => void;
}) {
  const { material: m, pathway, override, animation, prepTl } = resolution;
  const { addToBank } = useStore();
  const [saved, setSaved] = useState(false);

  function save() {
    addToBank(m.class);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1400);
  }

  return (
    <section aria-live="polite">
      <article className="card">
        <div className="eyebrow">Ito ay</div>
        <div className="what">{displayName(m)}</div>
        <div className="trade">{subName(m)}</div>

        <div className={`verdict ${animation}`}>
          <div className="v-label">{pathway.label_tl}</div>
          <div className="v-en">{pathway.label_en}</div>

          {/* An override changed the answer, so the price it replaced would
              contradict the verdict. Otherwise always state the market position —
              including when there isn't one, which is the single most important
              fact about a sachet. */}
          {override ? (
            <div className="v-en">{override.reason_tl}</div>
          ) : m.often_refused ? (
            <>
              <div className="v-price">Madalas tinatanggihan</div>
              <div className="v-en">
                May nominal na presyo ({m.price.display}) pero karamihan ng junkshop ay ayaw
                tumanggap. Tumawag muna bago magdala.
              </div>
            </>
          ) : (
            <div className="v-price">{m.price.display}</div>
          )}
        </div>

        <div className="how">
          <strong>Paano</strong>
          <div>{prepTl}</div>
        </div>

        {m.is_critical_class && (
          <div className="flag">
            Ito ang pangunahing bumabara sa mga kanal at sapa ng Cainta. Walang recycling
            market — ang tanging magagawa ay huwag itong mapunta sa tubig.
          </div>
        )}

        {showsPriceCaveat(resolution) && (
          <div className="note">
            Tinatayang presyo — wala pang na-verify na junkshop sa Cainta. Magtanong sa
            tindahan bago magdala.
          </div>
        )}

        <LegalBlock material={m} />
      </article>

      <div className="actions">
        <button className="primary" onClick={onFlow}>
          Ipakita ang daloy
        </button>
        <button className="secondary" onClick={save}>
          {saved ? 'Naidagdag ✓' : 'Idagdag sa Bote Bank'}
        </button>
      </div>

      <button className="linkish wide" onClick={onBack}>
        Baguhin ang detalye
      </button>
      <button className="linkish wide" onClick={onAgain}>
        Mag-scan ulit
      </button>
    </section>
  );
}

/**
 * The §7.8 guardrail, rendered.
 *
 * While `presentable_as_official` is false the card names the law but explicitly
 * disclaims authorship — "Kaugnay na batas" (related law), never "Batay sa" (based
 * on). Getting this backwards would put words in the municipality's mouth.
 */
function LegalBlock({ material }: { material: Material }) {
  if (material.citations.length === 0) return null;

  const names = material.citations.map((c) => c.citation).join('; ');

  return (
    <div className="legal">
      {material.presentable_as_official ? (
        <div>Batay sa: {names}</div>
      ) : (
        <>
          <div>Kaugnay na batas: {names}</div>
          <div className="unverified">
            Hindi pa nabe-verify sa orihinal na dokumento. Hindi ito opisyal na pahayag ng
            Pamahalaang Bayan ng Cainta.
          </div>
        </>
      )}
    </div>
  );
}
