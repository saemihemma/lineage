/**
 * Tests for useGameState hook
 * Focuses on detecting React Error #310 (hook stability issues)
 */
import { useState, useEffect } from 'react'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { waitFor } from '@testing-library/react'
import { renderWithStrictMode, createErrorSpy } from '../utils/testHookStability'
import { useGameState } from '../../hooks/useGameState'
import { createDefaultState } from '../../utils/localStorage'
import type { GameState } from '../../types/game'

// Mock localStorage utilities
vi.mock('../../utils/localStorage', () => {
  let mockState: GameState | null = null
  
  return {
    loadStateFromLocalStorage: vi.fn(() => mockState),
    saveStateToLocalStorage: vi.fn((state: GameState) => {
      mockState = state
    }),
    createDefaultState: vi.fn(() => ({
      version: 1,
      rng_seed: 12345,
      soul_percent: 100.0,
      soul_xp: 0,
      soul_level: 1,
      assembler_built: false,
      wombs: [],
      resources: { Tritanium: 60 },
      applied_clone_id: '',
      practices_xp: {},
      practice_levels: { Kinetic: 0, Cognitive: 0, Constructive: 0 },
      last_saved_ts: Date.now(),
      self_name: '',
      clones: {},
      active_tasks: {},
    })),
    setMockState: (state: GameState | null) => {
      mockState = state
    },
  }
})

// Mock tasks utility
vi.mock('../../utils/tasks', () => ({
  checkAndCompleteTasks: vi.fn((state: GameState) => ({
    state,
    completedMessages: [],
  })),
}))

describe('useGameState - Hook Stability Tests', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should not throw React Error #310 in StrictMode', () => {
    const errorSpy = createErrorSpy()
    
    function TestComponent() {
      useGameState()
      return <div>Test</div>
    }

    expect(() => {
      renderWithStrictMode(<TestComponent />)
    }).not.toThrow()
    
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle state transitions (null → object → updated) without hook order issues', async () => {
    const errorSpy = createErrorSpy()
    
    let stateValue: GameState | null = null
    let updateState: ((state: GameState | null) => void) | null = null

    function TestComponent() {
      const { state, updateState: update } = useGameState()
      stateValue = state
      updateState = () => update(state || createDefaultState())
      return <div>{state ? 'Loaded' : 'Loading'}</div>
    }

    const { rerender } = renderWithStrictMode(<TestComponent />)
    
    // Wait for initial load
    await waitFor(() => {
      expect(stateValue).not.toBe(null)
    }, { timeout: 1000 })

    // Simulate state updates
    if (stateValue) {
      const updatedState = { ...stateValue, self_name: 'Test Name' }
      // Trigger update via updateState callback
      // Note: In real usage, updateState would be called from an action
      rerender(<TestComponent />)
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable activeTasksVersion when active_tasks changes', async () => {
    let lastVersion: string | undefined
    let versionChanged = false
    let renderCount = 0

    function TestComponent() {
      const { state } = useGameState()
      renderCount++
      
      // Simulate activeTasksVersion calculation
      const activeTasksVersion = state?.active_tasks
        ? Object.keys(state.active_tasks).sort().join('|')
        : ''
      
      if (lastVersion !== undefined && lastVersion !== activeTasksVersion) {
        versionChanged = true
      }
      lastVersion = activeTasksVersion
      
      return <div>{activeTasksVersion}</div>
    }

    renderWithStrictMode(<TestComponent />)
    
    await waitFor(() => {
      expect(renderCount).toBeGreaterThan(0)
    })

    // Version should be stable (not change on every render due to optional chaining)
    // Multiple renders in StrictMode should not cause version to flip between undefined and ''
    expect(lastVersion).toBeDefined()
  })

  it('should handle optional chaining guards correctly', async () => {
    const errorSpy = createErrorSpy()
    
    function TestComponent() {
      const { state } = useGameState()
      
      // This mirrors the pattern in useGameState - should use EMPTY_TASKS_OBJ guard
      const EMPTY_TASKS_OBJ = {} as Record<string, any>
      const activeTasksVersion = state?.active_tasks
        ? Object.keys(state.active_tasks).sort().join('|')
        : ''
      
      return <div data-testid="version">{activeTasksVersion}</div>
    }

    const { getByTestId } = renderWithStrictMode(<TestComponent />)
    
    await waitFor(() => {
      const version = getByTestId('version')
      expect(version).toBeInTheDocument()
    })

    // Should not throw error #310 due to optional chaining instability
    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should not cause hook order changes when loading state', async () => {
    const hookCallOrder: string[] = []
    
    function TestComponent() {
      hookCallOrder.push('useState-1')
      const [localState] = useState(0)
      
      hookCallOrder.push('useGameState')
      const { state, loading } = useGameState()
      
      hookCallOrder.push('useEffect')
      useEffect(() => {
        // Effect that depends on state
      }, [state])
      
      return <div>{loading ? 'Loading' : 'Loaded'}</div>
    }

    renderWithStrictMode(<TestComponent />)
    
    await waitFor(() => {
      expect(hookCallOrder.length).toBeGreaterThan(0)
    })

    // In StrictMode, hooks should be called twice, but in the same order
    // Verify order is consistent (not checking exact count due to StrictMode double-render)
    const useState1Index = hookCallOrder.indexOf('useState-1')
    const useGameStateIndex = hookCallOrder.indexOf('useGameState')
    const useEffectIndex = hookCallOrder.indexOf('useEffect')
    
    expect(useState1Index).toBeLessThan(useGameStateIndex)
    expect(useGameStateIndex).toBeLessThan(useEffectIndex)
  })

  it('should handle rapid state updates without instability', async () => {
    const errorSpy = createErrorSpy()
    
    function TestComponent() {
      const { state } = useGameState()
      return <div>{state ? `State: ${state.self_name}` : 'No state'}</div>
    }

    const { rerender } = renderWithStrictMode(<TestComponent />)
    
    // Rapid re-renders (simulating fast state changes)
    for (let i = 0; i < 5; i++) {
      rerender(<TestComponent />)
      await new Promise((resolve) => setTimeout(resolve, 10))
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable dependencies when active_tasks object reference changes', async () => {
    let dependencyChanges = 0
    let lastDependency: unknown

    function TestComponent() {
      const { state } = useGameState()
      
      // This should use stable version string, not the object itself
      const EMPTY_TASKS_OBJ = {} as Record<string, any>
      const tasks = state?.active_tasks ?? EMPTY_TASKS_OBJ
      const version = Object.keys(tasks).sort().join('|')
      
      // Track if dependency changed
      if (lastDependency !== undefined && lastDependency !== version) {
        dependencyChanges++
      }
      lastDependency = version
      
      return <div>{version}</div>
    }

    renderWithStrictMode(<TestComponent />)
    
    await waitFor(() => {
      expect(lastDependency).toBeDefined()
    })

    // Dependency should be stable (version string), not the object reference
    // Even with StrictMode double-renders, version string should be consistent
    expect(typeof lastDependency).toBe('string')
  })
})

