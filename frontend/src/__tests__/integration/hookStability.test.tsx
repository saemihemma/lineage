/**
 * Integration tests for React Error #310
 * Tests the full app flow with realistic state transitions
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { renderWithStrictMode, createErrorSpy, waitForEffects } from '../utils/testHookStability'
import { App } from '../../App'
import { createDefaultState } from '../../utils/localStorage'
import type { GameState } from '../../types/game'

// Mock all APIs to avoid network calls
vi.mock('../../api/game', () => ({
  gameAPI: {
    gatherResource: vi.fn().mockResolvedValue({ success: true }),
    runExpedition: vi.fn().mockResolvedValue({ success: true }),
    uploadClone: vi.fn().mockResolvedValue({ success: true }),
    repairWomb: vi.fn().mockResolvedValue({ success: true }),
    saveState: vi.fn().mockResolvedValue({ success: true }),
  },
}))

vi.mock('../../api/events', () => ({
  eventsAPI: {
    getEventsFeed: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('../../api/limits', () => ({
  limitsAPI: {
    getStatus: vi.fn().mockResolvedValue(null),
  },
}))

describe('Integration Tests - React Error #310', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should not throw React Error #310 when navigating through app screens', async () => {
    const errorSpy = createErrorSpy()

    // Start at briefing screen
    const { rerender } = renderWithStrictMode(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    )

    await waitForEffects()

    // Navigate to loading screen
    rerender(
      <MemoryRouter initialEntries={['/loading']}>
        <App />
      </MemoryRouter>
    )

    await waitForEffects()

    // Navigate to simulation screen
    rerender(
      <MemoryRouter initialEntries={['/simulation']}>
        <App />
      </MemoryRouter>
    )

    await waitForEffects()

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle rapid state changes with active tasks', async () => {
    const errorSpy = createErrorSpy()

    // Set up state with active tasks
    const stateWithTasks: GameState = {
      ...createDefaultState(),
      active_tasks: {
        task1: {
          id: 'task1',
          type: 'gather_resource',
          resource: 'Tritanium',
          start_time: Date.now() / 1000,
          duration: 5,
        },
      },
    }

    localStorage.setItem('lineage_game_state', JSON.stringify(stateWithTasks))

    renderWithStrictMode(
      <MemoryRouter initialEntries={['/simulation']}>
        <App />
      </MemoryRouter>
    )

    // Wait for effects and state transitions
    await waitForEffects()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Simulate task completing (remove from active_tasks)
    const stateAfterTask: GameState = {
      ...stateWithTasks,
      active_tasks: {},
    }
    localStorage.setItem('lineage_game_state', JSON.stringify(stateAfterTask))

    await waitForEffects()
    await new Promise((resolve) => setTimeout(resolve, 100))

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle state changing from null to object repeatedly', async () => {
    const errorSpy = createErrorSpy()

    const { rerender } = renderWithStrictMode(
      <MemoryRouter initialEntries={['/simulation']}>
        <App />
      </MemoryRouter>
    )

    // Rapidly change between states
    for (let i = 0; i < 5; i++) {
      // Clear state
      localStorage.removeItem('lineage_game_state')
      rerender(
        <MemoryRouter initialEntries={['/simulation']}>
          <App />
        </MemoryRouter>
      )
      await waitForEffects()

      // Add state
      localStorage.setItem('lineage_game_state', JSON.stringify(createDefaultState()))
      rerender(
        <MemoryRouter initialEntries={['/simulation']}>
          <App />
        </MemoryRouter>
      )
      await waitForEffects()
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle rapid active_tasks changes without hook instability', async () => {
    const errorSpy = createErrorSpy()

    const baseState = createDefaultState()

    // Start with no tasks
    localStorage.setItem('lineage_game_state', JSON.stringify(baseState))

    const { rerender } = renderWithStrictMode(
      <MemoryRouter initialEntries={['/simulation']}>
        <App />
      </MemoryRouter>
    )

    await waitForEffects()

    // Rapidly add and remove tasks
    for (let i = 0; i < 3; i++) {
      const withTasks: GameState = {
        ...baseState,
        active_tasks: {
          [`task${i}`]: {
            id: `task${i}`,
            type: 'gather_resource',
            resource: 'Tritanium',
            start_time: Date.now() / 1000,
            duration: 5,
          },
        },
      }
      localStorage.setItem('lineage_game_state', JSON.stringify(withTasks))
      rerender(
        <MemoryRouter initialEntries={['/simulation']}>
          <App />
        </MemoryRouter>
      )
      await waitForEffects()

      // Remove tasks
      localStorage.setItem('lineage_game_state', JSON.stringify(baseState))
      rerender(
        <MemoryRouter initialEntries={['/simulation']}>
          <App />
        </MemoryRouter>
      )
      await waitForEffects()
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle visibility changes (tab switching) without hook issues', async () => {
    const errorSpy = createErrorSpy()

    renderWithStrictMode(
      <MemoryRouter initialEntries={['/simulation']}>
        <App />
      </MemoryRouter>
    )

    await waitForEffects()

    // Simulate tab visibility changes
    Object.defineProperty(document, 'visibilityState', {
      writable: true,
      value: 'hidden',
      configurable: true,
    })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitForEffects()

    Object.defineProperty(document, 'visibilityState', {
      writable: true,
      value: 'visible',
      configurable: true,
    })
    document.dispatchEvent(new Event('visibilitychange'))

    await waitForEffects()

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})

