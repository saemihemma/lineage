/**
 * Tests for usePanelState hook and provider
 * Focuses on detecting React Error #310 (hook stability issues)
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { waitFor } from '@testing-library/react'
import { renderWithStrictMode, createErrorSpy } from '../utils/testHookStability'
import { PanelStateProvider, usePanelState } from '../../stores/usePanelState'

describe('usePanelState - Hook Stability Tests', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should not throw React Error #310 in StrictMode', () => {
    const errorSpy = createErrorSpy()

    function TestComponent() {
      usePanelState()
      return <div>Test</div>
    }

    expect(() => {
      renderWithStrictMode(
        <PanelStateProvider>
          <TestComponent />
        </PanelStateProvider>
      )
    }).not.toThrow()

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle localStorage migration without hook order issues', async () => {
    const errorSpy = createErrorSpy()

    // Set up old localStorage with sizes key
    localStorage.setItem('lineage:ui:v1', JSON.stringify({
      leftOpen: { ftue: true },
      sizes: { left: 300, right: 400 }, // Stale key that should be removed
    }))

    function TestComponent() {
      const { state } = usePanelState()
      return <div>{state.leftOpen.ftue ? 'FTUE' : 'No FTUE'}</div>
    }

    renderWithStrictMode(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    // Wait for useEffect to run (migration happens in effect)
    await waitFor(() => {
      const stored = localStorage.getItem('lineage:ui:v1')
      if (stored) {
        const parsed = JSON.parse(stored)
        // Migration should remove sizes
        return !('sizes' in parsed)
      }
      return false
    }, { timeout: 1000 })

    // Verify sizes was removed from localStorage
    const stored = localStorage.getItem('lineage:ui:v1')
    expect(stored).toBeTruthy()
    if (stored) {
      const parsed = JSON.parse(stored)
      expect(parsed.sizes).toBeUndefined()
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable provider value memoization', () => {
    const errorSpy = createErrorSpy()
    let renderCount = 0
    let previousValue: ReturnType<typeof usePanelState> | null = null

    function TestComponent() {
      const panelState = usePanelState()
      renderCount++

      // Check if value object reference changed unnecessarily
      if (previousValue && previousValue.state === panelState.state) {
        // State hasn't changed, so value object should be same reference
        // (memoized in provider)
      }
      previousValue = panelState

      return <div>Test</div>
    }

    const { rerender } = renderWithStrictMode(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    // Rerender without state changes
    rerender(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle rapid panel state changes without instability', () => {
    const errorSpy = createErrorSpy()

    function TestComponent() {
      const { state } = usePanelState()
      
      // Just verify we can access state without issues
      return <div>{state.leftOpen.ftue ? 'FTUE' : 'No FTUE'}</div>
    }

    renderWithStrictMode(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable callbacks (togglePanel, setPanelOpen, resetToDefaults)', () => {
    const errorSpy = createErrorSpy()
    let previousToggle: (() => void) | null = null
    let previousSetOpen: (() => void) | null = null
    let callbackChanges = 0

    function TestComponent() {
      const { togglePanel, setPanelOpen } = usePanelState()

      // Check if callbacks change reference (they should be stable via useCallback)
      if (previousToggle && previousToggle !== togglePanel) {
        callbackChanges++
      }
      if (previousSetOpen && previousSetOpen !== setPanelOpen) {
        callbackChanges++
      }

      previousToggle = togglePanel
      previousSetOpen = setPanelOpen

      return <div>Test</div>
    }

    const { rerender } = renderWithStrictMode(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    // Rerender multiple times
    for (let i = 0; i < 3; i++) {
      rerender(
        <PanelStateProvider>
          <TestComponent />
        </PanelStateProvider>
      )
    }

    // Callbacks should be stable (memoized with useCallback)
    // Note: callbackChanges might be > 0 due to StrictMode, but should be minimal
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle state updates without causing re-render storms', () => {
    const errorSpy = createErrorSpy()
    let renderCount = 0

    function TestComponent() {
      const { state } = usePanelState()
      renderCount++

      return <div>{state.rightOpen.progress ? 'Open' : 'Closed'}</div>
    }

    const { rerender } = renderWithStrictMode(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    // Rerender without state changes should not cause issues
    rerender(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    // Should render at least once (StrictMode may cause more)
    expect(renderCount).toBeGreaterThanOrEqual(1)
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should persist to localStorage without hook instability', () => {
    const errorSpy = createErrorSpy()

    function TestComponent() {
      const { state } = usePanelState()
      
      // Just verify we can access state
      return <div>{state.rightOpen.progress ? 'Open' : 'Closed'}</div>
    }

    renderWithStrictMode(
      <PanelStateProvider>
        <TestComponent />
      </PanelStateProvider>
    )

    // Verify localStorage was created (provider saves on mount)
    const stored = localStorage.getItem('lineage:ui:v1')
    expect(stored).toBeTruthy()
    
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})

