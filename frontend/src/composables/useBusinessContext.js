import { inject } from 'vue'
export const businessContextKey = Symbol('business')
export function useBusinessContext() {
  const context = inject(businessContextKey)
  if (!context) throw new Error('Business context is required.')
  return context
}
