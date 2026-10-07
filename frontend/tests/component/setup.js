import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

// jsdom has no layout, ResizeObserver or SVG coordinate transforms. Only these
// browser boundaries are substituted; React, the editor and geometry stay real.
const originalMatrix = Object.getOwnPropertyDescriptor(SVGElement.prototype, 'getScreenCTM')
const originalScroll = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollIntoView')

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback) { this.callback = callback }
    observe(target) { this.callback([{ target, contentRect: { width: 800, height: 500 } }]) }
    disconnect() {}
  })
  // Component test coordinates are 1:1 with the SVG viewBox. Real viewport
  // scaling, scrolling and browser validation are exercised by Playwright.
  vi.stubGlobal('DOMPoint', class {
    constructor(x, y) { this.x = x; this.y = y }
    matrixTransform() { return { x: this.x, y: this.y } }
  })
  Object.defineProperty(SVGElement.prototype, 'getScreenCTM', {
    configurable: true, value: () => ({ inverse: () => ({}) }),
  })
  Object.defineProperty(Element.prototype, 'scrollIntoView', {
    configurable: true, value: vi.fn(),
  })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  if (originalMatrix) Object.defineProperty(SVGElement.prototype, 'getScreenCTM', originalMatrix)
  else delete SVGElement.prototype.getScreenCTM
  if (originalScroll) Object.defineProperty(Element.prototype, 'scrollIntoView', originalScroll)
  else delete Element.prototype.scrollIntoView
})
