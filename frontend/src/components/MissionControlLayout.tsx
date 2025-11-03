/**
 * MissionControlLayout - CSS Grid wrapper for Mission Control dashboard
 * Uses CSS variables for dynamic sizing from panel state
 */
import { useEffect, useRef, useCallback, type ReactNode } from 'react';
import { usePanelState } from '../stores/usePanelState';
import './MissionControlLayout.css';

interface MissionControlLayoutProps {
  children: ReactNode;
  topHud: ReactNode;
}

export function MissionControlLayout({ children, topHud }: MissionControlLayoutProps) {
  const { state, setPanelSize } = usePanelState();
  const leftResizeRef = useRef<HTMLDivElement>(null);
  const rightResizeRef = useRef<HTMLDivElement>(null);
  
  // Use refs to store latest values without causing re-renders
  const setPanelSizeRef = useRef(setPanelSize);
  const sizesRef = useRef(state.sizes);
  
  // Keep refs updated
  useEffect(() => {
    setPanelSizeRef.current = setPanelSize;
    sizesRef.current = state.sizes;
  }, [setPanelSize, state.sizes]);

  // Update CSS variables when panel sizes change
  useEffect(() => {
    const leftWidth = state.sizes?.leftPx ?? 320;
    const rightWidth = state.sizes?.rightPx ?? 360;
    const terminalHeight = state.sizes?.terminalPct ?? 30;

    document.documentElement.style.setProperty('--left-width', `${leftWidth}px`);
    document.documentElement.style.setProperty('--right-width', `${rightWidth}px`);
    document.documentElement.style.setProperty('--terminal-height', `${terminalHeight}%`);
  }, [state.sizes]);

  // Setup left resize handler - use callback ref pattern to ensure ref is attached
  const setupLeftResize = (handle: HTMLDivElement | null) => {
    if (!handle) return;

    // Remove any existing listeners first (cleanup)
    const existingCleanup = (handle as any)._resizeCleanup;
    if (existingCleanup) {
      existingCleanup();
    }

    let isResizing = false;
    let startX = 0;
    let startSize = 0;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      isResizing = true;
      startX = e.clientX;
      // Get current size from CSS variable or fallback
      startSize = parseFloat(document.documentElement.style.getPropertyValue('--left-width') || '320');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const delta = e.clientX - startX;
      const newSize = Math.max(200, Math.min(800, startSize + delta));
      document.documentElement.style.setProperty('--left-width', `${newSize}px`);
    };

    const handleMouseUp = () => {
      if (!isResizing) return;
      isResizing = false;
      const currentSize = parseFloat(document.documentElement.style.getPropertyValue('--left-width') || '320');
      // Use ref to avoid dependency on setPanelSize
      setPanelSizeRef.current('leftPx', currentSize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    handle.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // Store cleanup function on element for potential cleanup
    const cleanup = () => {
      handle.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    (handle as any)._resizeCleanup = cleanup;
  };

  // Setup right resize handler
  const setupRightResize = (handle: HTMLDivElement | null) => {
    if (!handle) return;

    // Remove any existing listeners first (cleanup)
    const existingCleanup = (handle as any)._resizeCleanup;
    if (existingCleanup) {
      existingCleanup();
    }

    let isResizing = false;
    let startX = 0;
    let startSize = 0;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      isResizing = true;
      startX = e.clientX;
      // Get current size from CSS variable or fallback
      startSize = parseFloat(document.documentElement.style.getPropertyValue('--right-width') || '360');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const delta = startX - e.clientX; // Inverted: dragging left increases size
      const newSize = Math.max(240, Math.min(800, startSize + delta));
      document.documentElement.style.setProperty('--right-width', `${newSize}px`);
    };

    const handleMouseUp = () => {
      if (!isResizing) return;
      isResizing = false;
      const currentSize = parseFloat(document.documentElement.style.getPropertyValue('--right-width') || '360');
      // Use ref to avoid dependency on setPanelSize
      setPanelSizeRef.current('rightPx', currentSize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    handle.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // Store cleanup function on element for potential cleanup
    const cleanup = () => {
      handle.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    (handle as any)._resizeCleanup = cleanup;
  };

  // Callback refs that set up handlers when elements are mounted
  // Use useCallback to prevent unnecessary re-setups on re-renders
  const leftResizeCallback = useCallback((handle: HTMLDivElement | null) => {
    leftResizeRef.current = handle;
    setupLeftResize(handle);
  }, []); // Stable - setup functions use refs, not closure variables

  const rightResizeCallback = useCallback((handle: HTMLDivElement | null) => {
    rightResizeRef.current = handle;
    setupRightResize(handle);
  }, []); // Stable - setup functions use refs, not closure variables

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (leftResizeRef.current) {
        const cleanup = (leftResizeRef.current as any)._resizeCleanup;
        if (cleanup) cleanup();
      }
      if (rightResizeRef.current) {
        const cleanup = (rightResizeRef.current as any)._resizeCleanup;
        if (cleanup) cleanup();
      }
    };
  }, []);

  return (
    <div className="mission-control-layout">
      <div className="mission-control-hud">
        {topHud}
      </div>
      <div className="mission-control-grid">
        {/* Left column resize handle (on right edge) */}
        <div
          ref={leftResizeCallback}
          className="resize-handle resize-handle-column resize-handle-left"
          aria-label="Resize left column"
        />
        {children}
        {/* Right column resize handle (on left edge) */}
        <div
          ref={rightResizeCallback}
          className="resize-handle resize-handle-column resize-handle-right"
          aria-label="Resize right column"
        />
      </div>
    </div>
  );
}

