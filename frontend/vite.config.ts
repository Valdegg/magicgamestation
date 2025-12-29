import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all addresses (0.0.0.0)
    allowedHosts: ['all', '.ngrok-free.app', '.ngrok.app', 'magic.ngrok.dev', 'app.playmagic.now'], // Allow ngrok hosts
  }
})
