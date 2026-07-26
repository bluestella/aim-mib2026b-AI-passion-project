'use client';

import { useEffect } from 'react';

/**
 * Registers the service worker after the app is interactive.
 *
 * Registration is deliberately best-effort and never blocks anything: offline
 * support is a bonus, and a failure here (unsupported browser, insecure origin,
 * blocked by policy) must not affect a user who simply wants to look up where a
 * bottle goes.
 *
 * Skipped in development, where a cached shell fights the dev server's HMR.
 */
export default function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production') return;
    if (!('serviceWorker' in navigator)) return;

    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Intentionally silent: nothing the user can act on.
    });
  }, []);

  return null;
}
