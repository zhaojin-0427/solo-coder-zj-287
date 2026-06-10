import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 9501,
    proxy: {
      '/api': {
        target: 'http://localhost:9502',
        changeOrigin: true,
      }
    }
  }
})
