import type { NextConfig } from 'next';

/**
 * Deliberately close to stock. This is a static, client-rendered app with no API
 * routes yet, so every page prerenders at build time and Vercel serves it from the
 * edge with zero configuration.
 *
 * `output: 'export'` is NOT set on purpose: Phase 5's junkshop price ticker and the
 * MENRO dashboard both need server routes, and turning static export on now would
 * have to be undone then.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,

  async headers() {
    return [
      {
        // The service worker must not be cached, or a deploy cannot replace it and
        // users keep a stale rules bundle. Everything else is content-hashed by Next.
        source: '/sw.js',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' }],
      },
    ];
  },
};

export default nextConfig;
