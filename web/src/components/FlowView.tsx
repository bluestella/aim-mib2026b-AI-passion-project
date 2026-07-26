'use client';

import { useCallback, useEffect, useState } from 'react';
import { RULES } from '@/lib/rules';
import { useReducedMotion } from '@/lib/useReducedMotion';
import type { Resolution } from '@/lib/types';

const STAGE_MS = 900;

/**
 * The Flow Simulation (plan §2.2), as a staged reveal.
 *
 * A diagram, never a map. Real OSM waterway geometry is a Phase-2 deliverable; a
 * stylised line drawn over a basemap would read as surveyed truth, so this renders
 * as a timeline and says plainly that it is schematic.
 *
 * Timers live in an effect keyed to the run counter, so React tears them down on
 * unmount. The vanilla version scheduled them from a click handler and had them
 * cancelled by the navigation that triggered the animation — a bug that only showed
 * up in a browser.
 */
export default function FlowView({
  resolution,
  barangay,
  onBack,
}: {
  resolution: Resolution;
  barangay: string;
  onBack: () => void;
}) {
  const path = RULES.flow[resolution.animation];
  const reduced = useReducedMotion();
  const [revealed, setRevealed] = useState(0);
  const [run, setRun] = useState(0);

  // Reduced motion is a rendering decision, not a state transition: derive the
  // count instead of writing it, so no one has to reason about which effect won.
  const visible = reduced ? path.stages.length : revealed;

  const replay = useCallback(() => {
    setRevealed(0);
    setRun((n) => n + 1);
  }, []);

  useEffect(() => {
    if (reduced) return;

    const timers = path.stages.map((_, i) =>
      window.setTimeout(() => setRevealed((n) => Math.max(n, i + 1)), i * STAGE_MS),
    );
    return () => timers.forEach(window.clearTimeout);
  }, [path.stages, reduced, run]);

  return (
    <section>
      <h2>{path.label_tl}</h2>

      <ol className={`flow ${resolution.animation}`}>
        {path.stages.map((stage, i) => (
          <li
            key={stage.id}
            className={[stage.terminal ? 'terminal' : '', i < visible ? 'on' : '']
              .filter(Boolean)
              .join(' ')}
          >
            <div className="s-label">{stage.label_tl}</div>
            <div className="s-detail">{stage.detail_tl}</div>
          </li>
        ))}
      </ol>

      <p className="schematic">
        Schematic ito — dayagram ng pangkalahatang direksyon, hindi mapa. Hindi pa namin
        nave-verify kung aling sapa ang dumadaloy mula sa Barangay {barangay}, kaya wala
        kaming pinapangalanang sapa.
      </p>

      <div className="actions">
        <button className="secondary" onClick={replay}>
          Ulitin
        </button>
        <button className="primary" onClick={onBack}>
          Balik sa card
        </button>
      </div>
    </section>
  );
}
