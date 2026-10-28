/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev the API runs separately (uvicorn on :8000); in production FastAPI serves this build.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
  build: {
    target: 'es2020',
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // heavy libraries live in their own long-cached chunks and load only with the pages that need them
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return undefined
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'react'
          if (/node_modules\/(leaflet|react-leaflet|@react-leaflet)/.test(id)) return 'leaflet'
          if (/node_modules\/(recharts|d3-|victory-vendor|recharts-scale|internmap|lodash|eventemitter3|decimal\.js-light|react-smooth|react-transition-group|fast-equals|tiny-invariant|clsx|prop-types|react-is|dom-helpers)/.test(id)) return 'charts'
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
