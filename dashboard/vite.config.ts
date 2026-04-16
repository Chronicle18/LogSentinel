import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Split heavy third-party deps off the main bundle so initial parse
    // doesn't wait on chart/axios code that's only needed for panels.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/recharts')) return 'recharts'
          if (
            id.includes('node_modules/react-dom') ||
            id.includes('node_modules/react/') ||
            id.includes('node_modules/axios')
          ) {
            return 'vendor'
          }
          return undefined
        },
      },
    },
  },
})
