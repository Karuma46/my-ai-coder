import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const configuredApiUrl = loadEnv(mode, '.', '').VITE_APP_API_URL
  const apiUrl = configuredApiUrl ? new URL(configuredApiUrl) : null
  const apiBasePath = apiUrl?.pathname.replace(/\/+$/, '') ?? ''

  return {
    plugins: [react(), tailwindcss()],
    server: apiUrl
      ? {
          proxy: {
            '/__api': {
              target: apiUrl.origin,
              changeOrigin: true,
              rewrite: (path) =>
                `${apiBasePath}${path.replace(/^\/__api/, '')}`,
            },
            '/__health': {
              target: apiUrl.origin,
              changeOrigin: true,
              rewrite: () => '/health',
            },
          },
        }
      : undefined,
  }
})
