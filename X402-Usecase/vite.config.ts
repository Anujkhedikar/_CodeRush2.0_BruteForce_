import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vitejs.dev/config/
export default defineConfig({
  // The built app is served by FastAPI under the /app route, so bundled
  // assets must be emitted with that path prefix (e.g. /app/assets/...).
  base: '/app/',
  plugins: [
    react(),
    nodePolyfills({
      globals: {
        Buffer: true,
      },
    }),
  ],
})
