/**
 * Tests for SimulationScreen component
 * Focuses on detecting React Error #310 (hook stability issues)
 * This is the most complex component with many hooks
 * 
 * Note: Due to complexity, we focus on basic hook stability checks
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { renderWithStrictMode, createErrorSpy } from '../utils/testHookStability'
import { SimulationScreen } from '../../screens/SimulationScreen'
import { PanelStateProvider } from '../../stores/usePanelState'
import { createDefaultState } from '../../utils/localStorage'

// Mock localStorage utilities
vi.mock('../../utils/localStorage', async () => {
  const actual = await vi.importActual('../../utils/localStorage')
  return {
    ...actual,
    loadStateFromLocalStorage: vi.fn(() => createDefaultState()),
    saveStateToLocalStorage: vi.fn(),
    createDefaultState: vi.fn(() => createDefaultState()),
  }
})

// Mock game API
vi.mock('../../api/game', () => ({
  gameAPI: {
    gatherResource: vi.fn().mockResolvedValue({ success: true }),
    runExpedition: vi.fn().mockResolvedValue({ success: true }),
    uploadClone: vi.fn().mockResolvedValue({ success: true }),
    repairWomb: vi.fn().mockResolvedValue({ success: true }),
    saveState: vi.fn().mockResolvedValue({ success: true }),
  },
}))

// Mock events API
vi.mock('../../api/events', () => ({
  eventsAPI: {
    getEventsFeed: vi.fn().mockResolvedValue([]),
  },
}))

describe('SimulationScreen - Hook Stability Tests', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should not throw React Error #310 in StrictMode', () => {
    const errorSpy = createErrorSpy()

    expect(() => {
      renderWithStrictMode(
        <MemoryRouter>
          <PanelStateProvider>
            <SimulationScreen />
          </PanelStateProvider>
        </MemoryRouter>
      )
    }).not.toThrow()

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable hook order during re-renders', () => {
    const errorSpy = createErrorSpy()

    const { rerender } = renderWithStrictMode(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    // Rerender multiple times to test hook stability
    for (let i = 0; i < 3; i++) {
      rerender(
        <MemoryRouter>
          <PanelStateProvider>
            <SimulationScreen />
          </PanelStateProvider>
        </MemoryRouter>
      )
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should handle rapid re-renders without instability', () => {
    const errorSpy = createErrorSpy()

    const { rerender } = renderWithStrictMode(
      <MemoryRouter>
        <PanelStateProvider>
          <SimulationScreen />
        </PanelStateProvider>
      </MemoryRouter>
    )

    // Rapid re-renders
    for (let i = 0; i < 5; i++) {
      rerender(
        <MemoryRouter>
          <PanelStateProvider>
            <SimulationScreen />
          </PanelStateProvider>
        </MemoryRouter>
      )
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})

