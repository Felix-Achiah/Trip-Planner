import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from 'tailwindcss'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  css: {
    postcss: {
      plugins: [tailwindcss()],
    },
  },
  base: '/',
  server: {
    historyApiFallback: true,  // Enable fallback routing for React Router
  },
  resolve: {
    alias: {
      // Optional: Add aliases if needed for other imports
    },
    dedupe: ['mapbox-gl', 'react-map-gl'],
  },
  optimizeDeps: {
    include: ['mapbox-gl', 'react-map-gl'], // Pre-bundle these dependencies
  },
})
