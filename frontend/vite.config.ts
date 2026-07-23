import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'VoceoStock',
        short_name: 'VoceoStock',
        description: 'Captura de inventario por voz',
        theme_color: '#0f172a',
      },
    }),
  ],
  server: {
    host: true,
    proxy: {
      '/api': process.env.VITE_API_PROXY ?? 'http://localhost:8000',
      '/health': process.env.VITE_API_PROXY ?? 'http://localhost:8000',
    },
  },
})
