import { createRouter, createWebHistory } from 'vue-router'
import { nextTick } from 'vue'
import LandingView from '../views/LandingView.vue'
import { site } from '../composables/useSite.js'
import { ownerSession } from '../composables/useOwnerSession.js'
import { createSessionGuard } from './guards.js'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    ...(site.isStorefront ? [{
      path: '/', component: () => import('../views/StorefrontLayout.vue'), children: [
        { path: '', name: 'storefront', component: () => import('../views/StorefrontView.vue'), meta: { title: 'Our products' } },
        { path: 'products/:productId', name: 'storefront-product', component: () => import('../views/StorefrontProductView.vue'), meta: { title: 'Product' } },
      ],
    }] : [{ path: '/', name: 'home', component: LandingView, meta: { title: 'A home for your business' }, beforeEnter: () => site.isAdmin ? '/businesses' : site.isLanding ? true : { name: 'not-found' } }]),
    { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue'), meta: { title: 'Create your business', admin: true, guestOnly: true } },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { title: 'Owner login', admin: true, guestOnly: true } },
    { path: '/registration/success/:slug', name: 'registration-success', component: () => import('../views/RegistrationSuccessView.vue'), meta: { title: 'Your business is ready', admin: true, requiresAuth: true } },
    { path: '/businesses', name: 'owner-home', component: () => import('../views/OwnerHomeView.vue'), meta: { title: 'Your businesses', admin: true, requiresAuth: true } },
    { path: '/businesses/:slug', component: () => import('../views/AdminBusinessLayout.vue'), meta: { admin: true, requiresAuth: true }, children: [
      { path: '', redirect: to => ({ name: 'products', params: { slug: to.params.slug } }) },
      { path: 'products', name: 'products', component: () => import('../views/ProductsView.vue'), meta: { title: 'Products' } },
      { path: 'settings', name: 'business-settings', component: () => import('../views/BusinessSettingsView.vue'), meta: { title: 'Business settings' } },
      { path: 'products/new', name: 'product-create', component: () => import('../views/ProductEditorView.vue'), meta: { title: 'Add product' } },
      { path: 'products/:productId/edit', name: 'product-edit', component: () => import('../views/ProductEditorView.vue'), meta: { title: 'Edit product' } },
    ] },
    ...(import.meta.env.DEV ? [{ path: '/development', component: () => import('../views/DevelopmentView.vue'), meta: { title: 'Development status' } }] : []),
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue'), meta: { title: 'Page unavailable' } },
  ],
})
router.beforeEach(createSessionGuard(ownerSession, site))
router.afterEach(async to => {
  document.title = `${to.meta.title || 'Your business online'} · BlissBiz`
  await nextTick()
  document.querySelector('main')?.focus()
})
export default router
