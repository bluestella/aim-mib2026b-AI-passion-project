'use client';

import { useSyncExternalStore } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

/**
 * Whether the user has asked for reduced motion.
 *
 * `matchMedia` is an external store, so it is read through `useSyncExternalStore`:
 * that gives a correct value on the very first client render instead of animating
 * once and then correcting itself, and it keeps working if the user flips the OS
 * setting while the app is open.
 *
 * Returns false during SSR — the server cannot know, and false means the animation
 * code path is chosen, which the first client render immediately corrects if needed.
 */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const media = window.matchMedia(QUERY);
      media.addEventListener('change', onChange);
      return () => media.removeEventListener('change', onChange);
    },
    () => window.matchMedia(QUERY).matches,
    () => false,
  );
}
