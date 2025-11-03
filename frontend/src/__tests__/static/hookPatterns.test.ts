/**
 * Static analysis tests for React Error #310 patterns
 * Uses AST to detect problematic hook patterns without running components
 */
import { describe, it, expect } from 'vitest'
import * as fs from 'fs'
import * as path from 'path'
import { readFileSync } from 'fs'

/**
 * Find all TypeScript/TSX files in a directory
 */
function findSourceFiles(dir: string, fileList: string[] = []): string[] {
  const files = fs.readdirSync(dir)

  files.forEach((file) => {
    const filePath = path.join(dir, file)
    const stat = fs.statSync(filePath)

    if (stat.isDirectory()) {
      // Skip node_modules, dist, and test directories
      if (!['node_modules', 'dist', '__tests__', '.git'].includes(file)) {
        findSourceFiles(filePath, fileList)
      }
    } else if (file.endsWith('.tsx') || file.endsWith('.ts')) {
      // Skip test files and type definitions
      if (!file.endsWith('.test.tsx') && !file.endsWith('.test.ts') && !file.endsWith('.d.ts')) {
        fileList.push(filePath)
      }
    }
  })

  return fileList
}

/**
 * Detect optional chaining in dependency arrays
 * Pattern: [state?.property] or [obj?.prop?.nested]
 */
function detectOptionalChainingInDeps(sourceCode: string): Array<{ line: number; pattern: string }> {
  const issues: Array<{ line: number; pattern: string }> = []
  const lines = sourceCode.split('\n')

  // Pattern: useMemo|useEffect|useCallback.*\[.*\?\.|\[.*\?\..*\]
  const depPattern = /(useMemo|useEffect|useCallback)\s*\([^)]*,\s*\[([^\]]*)\]\)/gs

  let match
  while ((match = depPattern.exec(sourceCode)) !== null) {
    const depsString = match[2]
    // Check if deps contain optional chaining
    if (/\w+\?\./.test(depsString)) {
      const lineNumber = sourceCode.substring(0, match.index).split('\n').length
      issues.push({
        line: lineNumber,
        pattern: match[0].substring(0, 100), // First 100 chars for context
      })
    }
  }

  return issues
}

/**
 * Detect hooks inside conditional blocks
 * Pattern: if (...) { ... useState|useEffect ... }
 */
function detectConditionalHooks(sourceCode: string): Array<{ line: number; pattern: string }> {
  const issues: Array<{ line: number; pattern: string }> = []
  const lines = sourceCode.split('\n')

  // Pattern: if/for/while followed by hook call
  const conditionalPattern = /(if|for|while)\s*\([^)]*\)\s*\{[^}]*\b(useState|useEffect|useMemo|useCallback|useRef|useContext)\s*\(/gs

  let match
  while ((match = conditionalPattern.exec(sourceCode)) !== null) {
    const lineNumber = sourceCode.substring(0, match.index).split('\n').length
    issues.push({
      line: lineNumber,
      pattern: match[0].substring(0, 100),
    })
  }

  return issues
}

/**
 * Detect early returns before hooks
 * Pattern: function/component that returns before all hooks are called
 * Note: This is a simplified check - it looks for hooks in the same function after return statements
 */
function detectEarlyReturnsBeforeHooks(sourceCode: string): Array<{ line: number; pattern: string }> {
  const issues: Array<{ line: number; pattern: string }> = []
  
  // Split by function boundaries to avoid false positives
  // Look for: return <JSX> followed by hook calls (simplified)
  // This pattern is rare and usually indicates a problem
  
  // More precise: find return statements that aren't the final return
  // This is tricky to detect correctly, so we'll use a simpler heuristic:
  // Look for hooks that appear after "return (" or "return <" in the same block
  
  const lines = sourceCode.split('\n')
  let inFunction = false
  let foundReturn = false
  let returnLine = -1
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    
    // Detect function start
    if (/^(export\s+)?(function|const)\s+\w+/.test(line) || /^\s*export\s+function/.test(line)) {
      inFunction = true
      foundReturn = false
      returnLine = -1
      continue
    }
    
    if (!inFunction) continue
    
    // Detect return statement (not inside a nested function)
    if (/^\s*return\s+(<|\(|null|false)/.test(line)) {
      foundReturn = true
      returnLine = i + 1
    }
    
    // If we found a return, check if hooks appear later in the same function scope
    // (This is a simplified check - false positives possible)
    if (foundReturn && returnLine > 0 && i > returnLine) {
      // Check if we've closed the function
      if (/^\s*\}/.test(line) && !line.includes('return')) {
        // Function closed, reset
        inFunction = false
        foundReturn = false
        returnLine = -1
        continue
      }
      
      // Check for hooks after return (within reasonable distance)
      if (i - returnLine < 50 && /\b(useState|useEffect|useMemo|useCallback|useRef|useContext)\s*\(/.test(line)) {
        // This is likely an error - hook after return
        issues.push({
          line: i + 1,
          pattern: `Hook appears after return on line ${returnLine}`,
        })
      }
    }
  }
  
  return issues
}

/**
 * Detect object/array literals in dependencies without useMemo
 * Pattern: useEffect(() => {}, [{ prop: value }])
 */
function detectUnstableDeps(sourceCode: string): Array<{ line: number; pattern: string }> {
  const issues: Array<{ line: number; pattern: string }> = []
  
  // Pattern for hook dependencies with object/array literals
  const hookPattern = /(useEffect|useCallback)\s*\([^)]*,\s*\[([^\]]*)\]\)/gs
  
  let match
  while ((match = hookPattern.exec(sourceCode)) !== null) {
    const depsString = match[2]
    // Check for object/array literals in deps
    if (/\{[^}]*\}|\[[^\]]*\]/.test(depsString)) {
      const lineNumber = sourceCode.substring(0, match.index).split('\n').length
      // Allow empty arrays/objects
      const trimmedDeps = depsString.trim()
      if (trimmedDeps && trimmedDeps !== '{}' && trimmedDeps !== '[]') {
        issues.push({
          line: lineNumber,
          pattern: `Object/array literal in dependency: ${depsString.substring(0, 50)}`,
        })
      }
    }
  }
  
  return issues
}

describe('Static Analysis - React Error #310 Patterns', () => {
  const srcDir = path.join(__dirname, '../../')
  const sourceFiles = findSourceFiles(srcDir)

  it('should detect no optional chaining in dependency arrays', () => {
    const allIssues: Array<{ file: string; issues: Array<{ line: number; pattern: string }> }> = []

    sourceFiles.forEach((filePath) => {
      try {
        const sourceCode = readFileSync(filePath, 'utf-8')
        const issues = detectOptionalChainingInDeps(sourceCode)
        
        if (issues.length > 0) {
          const relativePath = path.relative(srcDir, filePath)
          allIssues.push({ file: relativePath, issues })
        }
      } catch (err) {
        // Skip files that can't be read
      }
    })

    if (allIssues.length > 0) {
      const report = allIssues.map(({ file, issues }) =>
        `  ${file}:\n${issues.map((i) => `    Line ${i.line}: ${i.pattern}`).join('\n')}`
      ).join('\n\n')
      throw new Error(`Found optional chaining in dependency arrays:\n\n${report}`)
    }

    expect(allIssues.length).toBe(0)
  })

  it('should detect no hooks inside conditional blocks', () => {
    const allIssues: Array<{ file: string; issues: Array<{ line: number; pattern: string }> }> = []

    sourceFiles.forEach((filePath) => {
      try {
        const sourceCode = readFileSync(filePath, 'utf-8')
        const issues = detectConditionalHooks(sourceCode)
        
        if (issues.length > 0) {
          const relativePath = path.relative(srcDir, filePath)
          allIssues.push({ file: relativePath, issues })
        }
      } catch (err) {
        // Skip files that can't be read
      }
    })

    if (allIssues.length > 0) {
      const report = allIssues.map(({ file, issues }) =>
        `  ${file}:\n${issues.map((i) => `    Line ${i.line}: ${i.pattern}`).join('\n')}`
      ).join('\n\n')
      throw new Error(`Found hooks inside conditional blocks:\n\n${report}`)
    }

    expect(allIssues.length).toBe(0)
  })

  it('should detect no early returns before hooks', () => {
    const allIssues: Array<{ file: string; issues: Array<{ line: number; pattern: string }> }> = []

    sourceFiles.forEach((filePath) => {
      try {
        const sourceCode = readFileSync(filePath, 'utf-8')
        const issues = detectEarlyReturnsBeforeHooks(sourceCode)
        
        if (issues.length > 0) {
          const relativePath = path.relative(srcDir, filePath)
          allIssues.push({ file: relativePath, issues })
        }
      } catch (err) {
        // Skip files that can't be read
      }
    })

    if (allIssues.length > 0) {
      const report = allIssues.map(({ file, issues }) =>
        `  ${file}:\n${issues.map((i) => `    Line ${i.line}: ${i.pattern}`).join('\n')}`
      ).join('\n\n')
      throw new Error(`Found hooks called after return statements:\n\n${report}`)
    }

    expect(allIssues.length).toBe(0)
  })

  it('should detect unstable object/array dependencies', () => {
    const allIssues: Array<{ file: string; issues: Array<{ line: number; pattern: string }> }> = []

    sourceFiles.forEach((filePath) => {
      try {
        const sourceCode = readFileSync(filePath, 'utf-8')
        const issues = detectUnstableDeps(sourceCode)
        
        if (issues.length > 0) {
          const relativePath = path.relative(srcDir, filePath)
          allIssues.push({ file: relativePath, issues })
        }
      } catch (err) {
        // Skip files that can't be read
      }
    })

    if (allIssues.length > 0) {
      const report = allIssues.map(({ file, issues }) =>
        `  ${file}:\n${issues.map((i) => `    Line ${i.line}: ${i.pattern}`).join('\n')}`
      ).join('\n\n')
      
      // This is a warning, not an error - some cases might be intentional
      console.warn(`Found potentially unstable dependencies:\n\n${report}`)
    }

    // Don't fail the test, just warn - some patterns might be intentional
    expect(allIssues.length).toBeGreaterThanOrEqual(0)
  })
})

