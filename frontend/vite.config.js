import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// ── Port config ───────────────────────────────────────────────────────────────
// Backend runs on 8000 by default (uvicorn main:app --reload)
// To run on 8001: uvicorn main:app --port 8001 --reload  (then change BACKEND below)
const BACKEND    = 'http://192.168.0.147:8000'
const AI_BACKEND = 'http://192.168.0.147:8000' // same process handles /analyze if added

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // All API calls go through /api prefix (useApi.js baseURL = '/api')
      '/api': {
        target: BACKEND,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // AI analysis endpoint (called directly with fetch('/analyze'))
      '/analyze': {
        target: AI_BACKEND,
        changeOrigin: true,
      },
    },
  },
})
