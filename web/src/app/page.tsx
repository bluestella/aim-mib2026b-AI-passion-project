'use client';

import { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { resolve } from '@/lib/rules';
import type { Selection } from '@/lib/types';
import SetupView from '@/components/SetupView';
import PickerView from '@/components/PickerView';
import ModifiersView from '@/components/ModifiersView';
import PathwayCard from '@/components/PathwayCard';
import FlowView from '@/components/FlowView';

type Step = 'picker' | 'modifiers' | 'card' | 'flow';

/**
 * The scan wizard.
 *
 * Kept as steps within one route rather than as four routes. The sequence is a
 * single decision — pick a thing, describe it, see the answer — and giving each step
 * a URL would invite someone to land on /card with no selection, which is a state
 * that has no meaning. The tabs are real routes because those *are* independent
 * destinations.
 */
export default function ScanPage() {
  const { barangay, hydrated, selection, setSelection } = useStore();
  const [requestedStep, setRequestedStep] = useState<Step>('picker');

  // Derived, not synchronised. Without a selection the only meaningful step is the
  // picker, so compute that during render rather than letting an effect correct a
  // step that was briefly wrong.
  const step: Step = selection ? requestedStep : 'picker';

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [step]);

  // Reserve the space rather than flashing the setup screen at someone who chose
  // their barangay months ago.
  if (!hydrated) return <div className="skeleton" aria-busy="true" />;

  if (!barangay) return <SetupView />;

  if (step === 'picker' || !selection) {
    return (
      <PickerView
        barangay={barangay}
        onPick={(materialClass) => {
          const fresh: Selection = { materialClass, flags: [], contaminated: false };
          setSelection(fresh);
          setRequestedStep('modifiers');
        }}
      />
    );
  }

  const resolution = resolve(selection);

  if (step === 'modifiers') {
    return (
      <ModifiersView
        selection={selection}
        onChange={setSelection}
        onContinue={() => setRequestedStep('card')}
        onBack={() => {
          setSelection(null);
          setRequestedStep('picker');
        }}
      />
    );
  }

  if (step === 'flow') {
    return (
      <FlowView
        resolution={resolution}
        barangay={barangay}
        onBack={() => setRequestedStep('card')}
      />
    );
  }

  return (
    <PathwayCard
      resolution={resolution}
      onFlow={() => setRequestedStep('flow')}
      onBack={() => setRequestedStep('modifiers')}
      onAgain={() => {
        setSelection(null);
        setRequestedStep('picker');
      }}
    />
  );
}
