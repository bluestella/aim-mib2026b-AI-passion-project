'use client';

/**
 * Client-side state: the chosen barangay, the Bote Bank ledger, and the in-progress
 * scan selection.
 *
 * Everything persisted here lives in localStorage and nowhere else. There is no
 * backend, no account, and no network write — which is the strongest possible
 * reading of plan §7.5, since data that never leaves the device cannot be
 * mishandled.
 *
 * localStorage is an external store, so it is read through `useSyncExternalStore`
 * rather than copied into React state inside an effect. That is not a style
 * preference: the effect approach renders once with empty state and then again with
 * the real state, which is exactly the flash of the setup screen that a returning
 * user should never see. `getServerSnapshot` gives SSR a defined, stable answer, and
 * `hydrated` rides along in the snapshot so consumers can tell "no barangay chosen"
 * apart from "not read yet".
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import type { Selection } from './types';

const STORE_KEY = 'daloy.v1';

export interface Persisted {
  barangay: string | null;
  bank: Record<string, number>;
}

interface Snapshot extends Persisted {
  /** False during SSR and hydration, true once localStorage has been read. */
  hydrated: boolean;
}

interface Store extends Snapshot {
  selection: Selection | null;
  setBarangay: (name: string) => void;
  setSelection: (selection: Selection | null) => void;
  addToBank: (materialClass: string) => void;
  removeFromBank: (materialClass: string) => void;
  clearBank: () => void;
}

const SERVER_SNAPSHOT: Snapshot = { barangay: null, bank: {}, hydrated: false };

/**
 * Cached so `getSnapshot` is referentially stable.
 *
 * `useSyncExternalStore` compares snapshots by identity and re-renders forever if a
 * fresh object comes back each call, so the parse happens once and the cache is
 * replaced only on an actual write.
 */
let cache: Snapshot | null = null;
const listeners = new Set<() => void>();

function read(): Snapshot {
  try {
    const raw = window.localStorage.getItem(STORE_KEY);
    if (!raw) return { ...SERVER_SNAPSHOT, hydrated: true };

    const parsed = JSON.parse(raw) as Partial<Persisted>;
    return {
      barangay: typeof parsed.barangay === 'string' ? parsed.barangay : null,
      bank:
        typeof parsed.bank === 'object' && parsed.bank !== null
          ? (parsed.bank as Record<string, number>)
          : {},
      hydrated: true,
    };
  } catch {
    // A corrupt or unavailable store is not worth an error screen. The app is fully
    // usable without it; it just forgets the barangay.
    return { ...SERVER_SNAPSHOT, hydrated: true };
  }
}

function getSnapshot(): Snapshot {
  cache ??= read();
  return cache;
}

function getServerSnapshot(): Snapshot {
  return SERVER_SNAPSHOT;
}

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  return () => {
    listeners.delete(onChange);
  };
}

function commit(next: Persisted): void {
  cache = { ...next, hydrated: true };
  try {
    window.localStorage.setItem(STORE_KEY, JSON.stringify(next));
  } catch {
    // Private browsing or a full quota. Losing persistence is acceptable; throwing
    // in the middle of a tap is not. The in-memory cache still updates, so the
    // session behaves normally.
  }
  listeners.forEach((listener) => listener());
}

const StoreContext = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  // The in-progress scan is intentionally NOT persisted: a half-finished selection
  // restored days later is noise, not a feature.
  const [selection, setSelection] = useState<Selection | null>(null);

  const mutate = useCallback((next: Persisted) => commit(next), []);

  const value = useMemo<Store>(() => {
    const { barangay, bank } = snapshot;
    return {
      ...snapshot,
      selection,
      setSelection,
      setBarangay: (name) => mutate({ barangay: name, bank }),
      addToBank: (materialClass) =>
        mutate({
          barangay,
          bank: { ...bank, [materialClass]: (bank[materialClass] ?? 0) + 1 },
        }),
      removeFromBank: (materialClass) =>
        mutate({
          barangay,
          bank: { ...bank, [materialClass]: Math.max(0, (bank[materialClass] ?? 0) - 1) },
        }),
      clearBank: () => mutate({ barangay, bank: {} }),
    };
  }, [snapshot, selection, mutate]);

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useStore must be used inside <StoreProvider>');
  return store;
}
