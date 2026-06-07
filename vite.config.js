import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Während der Entwicklung werden Anfragen an /api an den lokalen
// Token-Server (src/server.js, Standard-Port 8787) weitergeleitet,
// damit der ElevenLabs API-Key nicht im Browser landet.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8787',
        changeOrigin: true,
      },
    },
  },
})
