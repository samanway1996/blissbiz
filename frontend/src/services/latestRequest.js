export function createLatestRequest() {
  let version = 0
  let controller
  function cancel() { version += 1; controller?.abort() }
  return {
    cancel,
    async run(loader, callbacks) {
      cancel()
      const current = version
      controller = new AbortController()
      const signal = controller.signal
      callbacks.start?.()
      try {
        const result = await loader(signal)
        if (current === version) callbacks.success(result)
      } catch (error) {
        if (current === version && !signal.aborted) callbacks.error(error)
      } finally {
        if (current === version) callbacks.finish?.()
      }
    },
  }
}
