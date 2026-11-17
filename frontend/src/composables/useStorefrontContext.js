import { inject } from 'vue'
export const storefrontContextKey = Symbol('storefront')
export function useStorefrontContext() {
  const context = inject(storefrontContextKey)
  if (!context) throw new Error('Storefront context is required.')
  return context
}
