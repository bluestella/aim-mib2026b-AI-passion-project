import type { Verification } from '@/lib/types';

/**
 * Not dismissible, and rendered on the server from the compiled bundle.
 *
 * While the ordinances are unharvested and no junkshop has been surveyed, every
 * number in this app is provisional. A banner the user can close would let them
 * forget that; a build-time render means it cannot be suppressed by client state
 * either (plan §7.8, §10).
 */
export default function ProvisionalBanner({ verification }: { verification: Verification }) {
  if (verification.phase1_gate_met && verification.phase2_gate_met) return null;

  const bits: string[] = [];
  if (!verification.phase1_gate_met) {
    bits.push('Hindi pa nabe-verify ang mga ordinansa sa orihinal na dokumento');
  }
  if (!verification.phase2_gate_met) {
    bits.push('tinatayang presyo lamang ang ipinapakita');
  }

  return (
    <div className="provisional" role="note">
      <strong>Paunang bersyon.</strong> <span>{bits.join('; ')}.</span>
    </div>
  );
}
