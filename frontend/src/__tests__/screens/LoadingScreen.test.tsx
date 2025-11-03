/**
 * Tests for LoadingScreen component
 * Focuses on detecting React Error #310 (hook stability issues)
 */
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { renderWithStrictMode, createErrorSpy } from '../utils/testHookStability'
import { LoadingScreen } from '../../screens/LoadingScreen'

describe('LoadingScreen - Hook Stability Tests', () => {
  it('should not throw React Error #310 in StrictMode', () => {
    const errorSpy = createErrorSpy()

    expect(() => {
      renderWithStrictMode(
        <MemoryRouter>
          <LoadingScreen />
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
        <LoadingScreen />
      </MemoryRouter>
    )

    // Rerender multiple times
    for (let i = 0; i < 3; i++) {
      rerender(
        <MemoryRouter>
          <LoadingScreen />
        </MemoryRouter>
      )
    }

    expect(errorSpy.hasError310()).toBe(false)
    errorSpy.restore()
  })
})

