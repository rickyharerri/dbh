import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import { clearApiCache } from '../services/api'

afterEach(() => {
  cleanup()
  clearApiCache()
})

// jsdom lacks these browser APIs used by the app
window.scrollTo = (() => {}) as typeof window.scrollTo
Element.prototype.scrollIntoView = () => {}
class RO { observe() {} unobserve() {} disconnect() {} }
;(globalThis as unknown as { ResizeObserver: typeof RO }).ResizeObserver = RO
