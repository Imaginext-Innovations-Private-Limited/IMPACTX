import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    // react-globe.gl and this app both import three; keep a single copy so
    // scene objects, materials and geometries come from the same library.
    dedupe: ['three'],
  },
})
