/**
 * REAL integration tests - Uses actual hooks, no mocks
 * Tests the exact production scenario that causes React Error #310
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { renderWithStrictMode, createErrorSpy, waitForEffects } from '../utils/testHookStability'
import { SimulationScreen } from '../../screens/SimulationScreen'
import { PanelStateProvider } from '../../stores/usePanelState'
import { createDefaultState } from '../../utils/localStorage'
import type { GameState } from '../../types/game'

// Only mock external APIs, NOT the hooks
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

// Mock tasks utility to prevent actual task completion logic
vi.mock('../../utils/tasks', () => ({
  checkAndCompleteTasks: vi.fn((state: GameState) => ({
    state,
    completedMessages: [],
  })),
}))

describe('REAL Hook Stability Tests - Production Scenarios', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should handle state transition: null → object with active_tasks', async () => {
    const errorSpy = createErrorSpy()

    // Start with no state in localStorage (useGameState will return null initially)
    const { rerender } = renderWithStrictMode(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    // Now add state with active_tasks (simulating real state load)
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

    // Force re-render by updating localStorage and triggering state reload
    // This simulates the real scenario where state loads asynchronously
    rerender(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()
    await new Promise((resolve) => setTimeout(resolve, 100))

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle active_tasks changing: empty → populated → empty', async () => {
    const errorSpy = createErrorSpy()

    // Start with state having no tasks
    const emptyState = createDefaultState()
    localStorage.setItem('lineage_game_state', JSON.stringify(emptyState))

    const { rerender } = renderWithStrictMode(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    // Add tasks (simulates starting a gather action)
    const withTasks: GameState = {
      ...emptyState,
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

    localStorage.setItem('lineage_game_state', JSON.stringify(withTasks))
    rerender(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()
    await new Promise((resolve) => setTimeout(resolve, 100))

    // Remove tasks (simulates task completion)
    localStorage.setItem('lineage_game_state', JSON.stringify(emptyState))
    rerender(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()
    await new Promise((resolve) => setTimeout(resolve, 100))

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle rapid active_tasks updates (the real production bug scenario)', async () => {
    const errorSpy = createErrorSpy()

    const baseState = createDefaultState()
    localStorage.setItem('lineage_game_state', JSON.stringify(baseState))

    const { rerender } = renderWithStrictMode(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    // Rapidly toggle tasks - this is what causes the bug
    // active_tasks flips: undefined → {} → {task1} → {} → undefined
    for (let i = 0; i < 5; i++) {
      if (i % 2 === 0) {
        // Add task
        const withTask: GameState = {
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
        localStorage.setItem('lineage_game_state', JSON.stringify(withTask))
      } else {
        // Remove task (set to empty object, not undefined)
        const withoutTask: GameState = {
          ...baseState,
          active_tasks: {},
        }
        localStorage.setItem('lineage_game_state', JSON.stringify(withoutTask))
      }

      rerender(
        <MemoryRouter>
          <PanelStateProvider>
            <SimulationScreen />
          </PanelStateProvider>
        </MemoryRouter>
      )

      await waitForEffects()
      await new Promise((resolve) => setTimeout(resolve, 50))
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle state.active_tasks shape changes without hook instability', async () => {
    const errorSpy = createErrorSpy()

    // Test the exact scenario: active_tasks goes from undefined → {} → {task} → {}
    // This is where optional chaining in deps causes the bug

    // Step 1: No active_tasks (undefined)
    const state1: GameState = createDefaultState()
    delete (state1 as any).active_tasks
    localStorage.setItem('lineage_game_state', JSON.stringify(state1))

    const { rerender } = renderWithStrictMode(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    // Step 2: Empty object (not undefined)
    const state2: GameState = {
      ...state1,
      active_tasks: {},
    }
    localStorage.setItem('lineage_game_state', JSON.stringify(state2))
    rerender(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    // Step 3: With task
    const state3: GameState = {
      ...state2,
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
    localStorage.setItem('lineage_game_state', JSON.stringify(state3))
    rerender(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    // Step 4: Back to empty
    localStorage.setItem('lineage_game_state', JSON.stringify(state2))
    rerender(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    await waitForEffects()

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})

