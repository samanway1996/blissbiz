import { createApp } from 'vue'
import './style.css'

async function start() {
  try {
    const [{ default: App }, { default: router }] = await Promise.all([import('./App.vue'), import('./router/index.js')])
    const app = createApp(App)
    app.use(router)
    await router.isReady()
    app.mount('#app')
  } catch {
    const root = document.getElementById('app')
    root.textContent = 'BlissBiz could not start. Check that VITE_STOREFRONT_BASE_URL and VITE_ADMIN_BASE_URL match your frontend domain, then rebuild. If configuration is correct, reload to try again.'
    root.setAttribute('role', 'alert')
    root.className = 'configuration-error'
  }
}
start()
