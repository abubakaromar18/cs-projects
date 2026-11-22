import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // Library tests run in Node (which ships WebCrypto); component tests opt
    // into jsdom with a per-file `@vitest-environment jsdom` docblock.
    environment: 'node',
    include: ['test/**/*.test.{js,jsx}'],
  },
});
