/**
 * Test utilities for detecting React Error #310 (hook stability issues)
 */
import { StrictMode, createElement } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { render } from '@testing-library/react'
import type { RenderOptions } from '@testing-library/react'

/**
 * Wraps a component in React StrictMode to catch hook order issues
 * StrictMode double-renders components and will throw React Error #310
 * if hooks are called in different orders between renders
 */
export function renderWithStrictMode(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  const Wrapper = ({ children }: { children: ReactNode }) => {
    return createElement(StrictMode, null, children)
  }
  return render(ui, {
    wrapper: Wrapper,
    ...options,
  })
}

/**
 * Simulates state transitions to test hook stability
 * Tests: null → object → updated object
 */
export async function simulateStateTransitions<T>(
  component: ReactElement,
  stateUpdates: T[],
  updateCallback: (state: T | null) => void
) {
  const { rerender } = renderWithStrictMode(component)
  
  // Start with null state
  updateCallback(null)
  rerender(component)
  
  // Apply state updates sequentially
  for (const state of stateUpdates) {
    updateCallback(state)
    rerender(component)
    // Small delay to ensure effects have run
    await new Promise((resolve) => setTimeout(resolve, 10))
  }
}

/**
 * Mocks localStorage with a clean state for each test
 */
export function createMockLocalStorage() {
  const store: Record<string, string> = {}
  
  return {
    getItem: (key: string): string | null => store[key] || null,
    setItem: (key: string, value: string): void => {
      store[key] = String(value)
    },
    removeItem: (key: string): void => {
      delete store[key]
    },
    clear: (): void => {
      Object.keys(store).forEach((key) => delete store[key])
    },
    getStore: (): Record<string, string> => ({ ...store }),
  }
}

/**
 * Helper to count hook calls in a component
 * Useful for detecting hook count mismatches between renders
 */
export class HookCallCounter {
  private callCounts: Map<string, number> = new Map()
  
  increment(hookName: string): void {
    this.callCounts.set(hookName, (this.callCounts.get(hookName) || 0) + 1)
  }
  
  getCount(hookName: string): number {
    return this.callCounts.get(hookName) || 0
  }
  
  getAllCounts(): Record<string, number> {
    const result: Record<string, number> = {}
    this.callCounts.forEach((count, name) => {
      result[name] = count
    })
    return result
  }
  
  reset(): void {
    this.callCounts.clear()
  }
}

/**
 * Waits for all effects to complete
 * Useful for testing async operations in useEffect
 */
export async function waitForEffects() {
  // Wait for next tick to ensure all effects have run
  await new Promise((resolve) => setTimeout(resolve, 0))
}

/**
 * Simulates rapid state changes to test hook stability
 * Useful for detecting race conditions or unstable dependencies
 */
export async function simulateRapidUpdates<T>(
  updateCallback: (state: T) => void,
  states: T[],
  delay: number = 10
) {
  for (const state of states) {
    updateCallback(state)
    await new Promise((resolve) => setTimeout(resolve, delay))
  }
}

/**
 * Creates a spy on console.error to catch React Error #310
 * Returns a function to check if the error was thrown
 */
export function createErrorSpy() {
  const errors: Error[] = []
  const originalError = console.error
  
  console.error = (...args: unknown[]) => {
    const message = args[0]?.toString() || ''
    if (message.includes('Error #310') || message.includes('Rendered fewer hooks')) {
      errors.push(new Error(message))
    }
    originalError.apply(console, args)
  }
  
  return {
    getErrors: () => [...errors],
    hasError310: () => errors.some((e) => e.message.includes('Error #310')),
    restore: () => {
      console.error = originalError
    },
  }
}

/**
 * Helper to verify that all hooks are called unconditionally
 * Components should not have hooks inside if statements or loops
 */
export function verifyUnconditionalHooks(componentCode: string): boolean {
  // Simple heuristic: check if hooks appear after conditional statements
  // This is a basic check - full AST analysis should be done in static tests
  const conditionalPattern = /if\s*\([^)]*\)\s*\{[\s\S]*?(useState|useEffect|useMemo|useCallback|useRef)/;
  
  return !conditionalPattern.test(componentCode);
}

/**
 * Verifies that early returns happen after all hooks
 * All hooks must be called before any conditional returns
 */
export function verifyHookOrder(componentCode: string): boolean {
  // Extract function body (simplified check)
  const functionMatch = componentCode.match(/export\s+function\s+\w+\s*\([^)]*\)\s*\{([\s\S]*)\}/)
  if (!functionMatch) return true
  
  const body = functionMatch[1]
  const returnPattern = /return\s+[^;]+/
  
  // Find first hook and first return
  const hookNames = ['useState', 'useEffect', 'useMemo', 'useCallback', 'useRef', 'useContext']
  const firstHook = hookNames.reduce((earliest, hook) => {
    const index = body.indexOf(hook)
    return index !== -1 && (earliest === -1 || index < earliest) ? index : earliest
  }, -1)
  
  const firstReturn = body.search(returnPattern)
  
  // If no hooks or no early return, it's fine
  if (firstHook === -1 || firstReturn === -1) return true
  
  // All hooks must come before any return
  return firstHook < firstReturn
}

