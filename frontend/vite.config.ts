import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { mockApiPlugin } from './mock-server/index.ts'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const usaMock = !env.VITE_API || env.VITE_API === 'mock'

  return {
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
      ...(usaMock ? [mockApiPlugin()] : []),
    ],
    server: {
      host: true,
      // El mock atiende /api y /health directamente; el proxy solo aplica contra el backend real.
      proxy: usaMock
        ? undefined
        : {
            '/api': env.VITE_API_PROXY ?? 'http://localhost:8010',
            '/health': env.VITE_API_PROXY ?? 'http://localhost:8010',
            // C8: el progreso en vivo llega por el WebSocket real del backend.
            '/ws': { target: env.VITE_API_PROXY ?? 'http://localhost:8010', ws: true },
          },
    },
  }
})
