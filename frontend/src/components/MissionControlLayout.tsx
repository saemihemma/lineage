/**
 * MissionControlLayout - CSS Grid wrapper for Mission Control dashboard
 * Uses CSS variables for dynamic sizing from panel state
 */
import { useEffect, useRef, type ReactNode } from 'react';
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

  // Update CSS variables when panel sizes change
  useEffect(() => {
    const leftWidth = state.sizes.leftPx ?? 320;
    const rightWidth = state.sizes.rightPx ?? 360;
    const terminalHeight = state.sizes.terminalPct ?? 30;

    document.documentElement.style.setProperty('--left-width', `${leftWidth}px`);
    document.documentElement.style.setProperty('--right-width', `${rightWidth}px`);
    document.documentElement.style.setProperty('--terminal-height', `${terminalHeight}%`);
  }, [state.sizes]);

  // Left column resize (vertical handle on right edge of left column)
  useEffect(() => {
    const handle = leftResizeRef.current;
    if (!handle) return;

    let isResizing = false;
    let startX = 0;
    let startSize = 0;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      isResizing = true;
      startX = e.clientX;
      startSize = state.sizes.leftPx ?? 320;
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
      setPanelSize('leftPx', currentSize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    handle.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      handle.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [state.sizes.leftPx, setPanelSize]);

  // Right column resize (vertical handle on left edge of right column)
  useEffect(() => {
    const handle = rightResizeRef.current;
    if (!handle) return;

    let isResizing = false;
    let startX = 0;
    let startSize = 0;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      isResizing = true;
      startX = e.clientX;
      startSize = state.sizes.rightPx ?? 360;
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
      setPanelSize('rightPx', currentSize);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    handle.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      handle.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [state.sizes.rightPx, setPanelSize]);

  return (
    <div className="mission-control-layout">
      <div className="mission-control-hud">
        {topHud}
      </div>
      <div className="mission-control-grid">
        {/* Left column resize handle (on right edge) */}
        <div
          ref={leftResizeRef}
          className="resize-handle resize-handle-column resize-handle-left"
          aria-label="Resize left column"
        />
        {children}
        {/* Right column resize handle (on left edge) */}
        <div
          ref={rightResizeRef}
          className="resize-handle resize-handle-column resize-handle-right"
          aria-label="Resize right column"
        />
      </div>
    </div>
  );
}

