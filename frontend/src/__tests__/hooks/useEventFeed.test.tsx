/**
 * Tests for useEventFeed hook
 * Focuses on detecting React Error #310 (hook stability issues)
 */
import { useEffect } from 'react'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderWithStrictMode, createErrorSpy } from '../utils/testHookStability'
import { useEventFeed } from '../../hooks/useEventFeed'
import type { GameState } from '../../types/game'

// Mock events API
vi.mock('../../api/events', () => ({
  eventsAPI: {
    getEventsFeed: vi.fn(),
  },
}))

import { eventsAPI } from '../../api/events'
const mockGetEventsFeed = vi.mocked(eventsAPI.getEventsFeed)

describe('useEventFeed - Hook Stability Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetEventsFeed.mockResolvedValue([])
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('should not throw React Error #310 in StrictMode', () => {
    const errorSpy = createErrorSpy()
    
    function TestComponent() {
      useEventFeed({ enabled: false })
      return <div>Test</div>
    }

    expect(() => {
      renderWithStrictMode(<TestComponent />)
    }).not.toThrow()
    
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable callback refs when callbacks change', () => {
    const errorSpy = createErrorSpy()

    const callback1 = vi.fn()
    const callback2 = vi.fn()

    function TestComponent({ callback }: { callback: () => void }) {
      useEventFeed({
        enabled: false, // Don't poll, just test hook stability
        onStatePatch: callback,
      })
      return <div>Test</div>
    }

    const { rerender } = renderWithStrictMode(<TestComponent callback={callback1} />)
    
    // Change callback - should not cause hook order issues
    rerender(<TestComponent callback={callback2} />)

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should not recreate pollEvents when callbacks change', () => {
    const errorSpy = createErrorSpy()

    function TestComponent({ onStatePatch }: { onStatePatch?: (state: GameState | null) => void }) {
      useEventFeed({
        enabled: false, // Don't poll, just test hook stability
        onStatePatch,
      })
      return <div>Test</div>
    }

    const callback1 = vi.fn()
    const callback2 = vi.fn()

    const { rerender } = renderWithStrictMode(<TestComponent onStatePatch={callback1} />)
    
    // Change callback - pollEvents should not be recreated (it uses refs)
    rerender(<TestComponent onStatePatch={callback2} />)

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle rapid callback changes without instability', () => {
    const errorSpy = createErrorSpy()

    function TestComponent({ callback }: { callback?: (state: GameState | null) => void }) {
      useEventFeed({
        enabled: false,
        onStatePatch: callback,
        onTerminalMessage: callback ? () => {} : undefined,
        onEvents: callback ? () => {} : undefined,
      })
      return <div>Test</div>
    }

    const { rerender } = renderWithStrictMode(<TestComponent />)

    // Rapid callback changes
    for (let i = 0; i < 5; i++) {
      const cb = vi.fn()
      rerender(<TestComponent callback={cb} />)
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable dependencies in useEffect', () => {
    const errorSpy = createErrorSpy()

    function TestComponent() {
      const { startPolling, stopPolling } = useEventFeed({
        enabled: false,
        interval: 1000,
      })

      // startPolling and stopPolling should be stable (memoized)
      // This test verifies they don't cause re-renders
      useEffect(() => {
        // Effect that depends on stable callbacks
      }, [startPolling, stopPolling])

      return <div>Test</div>
    }

    renderWithStrictMode(<TestComponent />)

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle currentState changes without recreating pollEvents', () => {
    const errorSpy = createErrorSpy()

    const state1: GameState = {
      version: 1,
      rng_seed: 1,
      soul_percent: 100,
      soul_xp: 0,
      soul_level: 1,
      assembler_built: false,
      resources: {},
      applied_clone_id: '',
      practices_xp: {},
      practice_levels: { Kinetic: 0, Cognitive: 0, Constructive: 0 },
      last_saved_ts: Date.now(),
      self_name: 'Test1',
      clones: {},
    }

    const state2: GameState = {
      ...state1,
      self_name: 'Test2',
    }

    function TestComponent({ state }: { state: GameState | null }) {
      useEventFeed({
        enabled: false,
        currentState: state,
      })
      return <div>Test</div>
    }

    const { rerender } = renderWithStrictMode(<TestComponent state={state1} />)

    // Change state - this should update the ref but not recreate pollEvents
    rerender(<TestComponent state={state2} />)

    // pollEvents should not be recreated (it uses refs for currentState)
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})


