/**
 * Tests for FuelBar component
 * Focuses on detecting React Error #310 (hook stability issues)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithStrictMode, createErrorSpy } from '../utils/testHookStability'
import { FuelBar } from '../../components/FuelBar'
import { PanelStateProvider } from '../../stores/usePanelState'

// Mock limits API
vi.mock('../../api/limits', () => ({
  limitsAPI: {
    getStatus: vi.fn().mockResolvedValue(null), // Return null so component doesn't render
  },
}))

describe('FuelBar - Hook Stability Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not throw React Error #310 in StrictMode', () => {
    const errorSpy = createErrorSpy()

    expect(() => {
      renderWithStrictMode(
        <PanelStateProvider>
          <FuelBar />
        </PanelStateProvider>
      )
    }).not.toThrow()

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })

  it('should maintain stable hook order during re-renders', () => {
    const errorSpy = createErrorSpy()

    const { rerender } = renderWithStrictMode(
      <PanelStateProvider>
        <FuelBar />
      </PanelStateProvider>
    )

    // Rerender multiple times
    for (let i = 0; i < 3; i++) {
      rerender(
        <PanelStateProvider>
          <FuelBar />
        </PanelStateProvider>
      )
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})

