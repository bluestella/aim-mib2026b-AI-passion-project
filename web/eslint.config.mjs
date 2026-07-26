import next from 'eslint-config-next';

/**
 * eslint-config-next v16 ships a native flat config array, so it is spread directly.
 * The FlatCompat shim older Next templates use throws a circular-structure error on
 * it.
 */
const config = [
  ...next,
  {
    ignores: ['.next/**', 'node_modules/**', 'src/data/**', 'public/sw.js'],
  },
];

export default config;
