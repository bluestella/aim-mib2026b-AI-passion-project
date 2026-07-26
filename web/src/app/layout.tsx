import type { Metadata, Viewport } from 'next';
import { StoreProvider } from '@/lib/store';
import { RULES } from '@/lib/rules';
import TopBar from '@/components/TopBar';
import TabBar from '@/components/TabBar';
import ProvisionalBanner from '@/components/ProvisionalBanner';
import ServiceWorker from '@/components/ServiceWorker';
import './globals.css';

export const metadata: Metadata = {
  title: 'DALOY Scan — Saan Napupunta?',
  description:
    'Kung saan dapat mapunta ang basura ninyo sa Cainta, Rizal. Walang app na ida-download.',
  manifest: '/manifest.webmanifest',
  applicationName: 'DALOY Scan',
  appleWebApp: { capable: true, title: 'DALOY Scan', statusBarStyle: 'default' },
  icons: { icon: '/icon.svg', apple: '/icon.svg' },
};

export const viewport: Viewport = {
  themeColor: '#0d4f4a',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // lang="tl" — the app is Tagalog-first, with English as the secondary line.
    // Screen readers should pronounce it accordingly.
    <html lang="tl">
      <body>
        <StoreProvider>
          <TopBar />
          {/* Server-rendered from the bundle: the provisional state is a build-time
              fact, not something the client discovers. */}
          <ProvisionalBanner verification={RULES.verification} />
          <main id="main">{children}</main>
          <TabBar />
          <ServiceWorker />
        </StoreProvider>
      </body>
    </html>
  );
}
