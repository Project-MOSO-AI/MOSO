import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/chat': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/system': 'http://localhost:8000',
      '/memory': 'http://localhost:8000',
      '/execute': 'http://localhost:8000',
      '/plan': 'http://localhost:8000',
      '/skills': 'http://localhost:8000',
      '/identity': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
