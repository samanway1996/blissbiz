import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Override only for the optional isolated F09 fixture server; defaults stay unchanged.
const apiTarget = process.env.BLISSBIZ_TEST_API_TARGET || 'http://127.0.0.1:8000'
const target = new URL(apiTarget)
if (target.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname) || target.username || target.password || target.pathname !== '/' || target.search || target.hash) {
  throw new Error('The development API target must be a loopback HTTP origin.')
}

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    allowedHosts: ['.localhost'],
    port: 5173,
    strictPort: true,
    watch: { usePolling: true },
    proxy: {
      '/api': { target: apiTarget, changeOrigin: false },
      '/media': { target: apiTarget, changeOrigin: false },
    },
  },
})
