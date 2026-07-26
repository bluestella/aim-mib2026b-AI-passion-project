'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';

/**
 * The back affordance is deliberately not a blanket `router.back()`. The scan wizard
 * is a sequence of states within one route, so within `/` the page owns its own back
 * navigation; the top bar only offers back on the secondary tabs, where "back" always
 * means "return to scanning".
 */
export default function TopBar() {
  const pathname = usePathname();
  const router = useRouter();
  const onScan = pathname === '/';

  return (
    <header className="topbar">
      {onScan ? (
        <span style={{ width: 36, flex: 'none' }} aria-hidden="true" />
      ) : (
        <button className="back" onClick={() => router.push('/')} aria-label="Bumalik sa scan">
          ←
        </button>
      )}
      <h1>
        DALOY <span>Scan</span>
      </h1>
      <Link href="/privacy" className="iconbtn" aria-label="Tungkol sa app at privacy">
        ?
      </Link>
    </header>
  );
}
