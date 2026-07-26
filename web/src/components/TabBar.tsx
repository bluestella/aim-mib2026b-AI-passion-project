'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';

const TABS = [
  { href: '/', icon: '♻️', label: 'Scan' },
  { href: '/bote-bank', icon: '🏦', label: 'Bote Bank' },
  { href: '/junkshop', icon: '📍', label: 'Junkshop' },
  { href: '/privacy', icon: '🔒', label: 'Privacy' },
] as const;

export default function TabBar() {
  const pathname = usePathname();
  const { barangay, hydrated } = useStore();

  // Hidden until a barangay is chosen: the setup screen is a single decision and
  // navigation away from it would leave the app in a half-configured state. Also
  // hidden pre-hydration so the server and client agree on the first paint.
  if (!hydrated || !barangay) return null;

  return (
    <nav className="tabbar" aria-label="Pangunahing nabigasyon">
      {TABS.map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          className={pathname === tab.href ? 'active' : undefined}
          aria-current={pathname === tab.href ? 'page' : undefined}
        >
          <span aria-hidden="true">{tab.icon}</span>
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}
