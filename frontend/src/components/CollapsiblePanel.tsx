/**
 * CollapsiblePanel - Wrapper component that enhances existing .panel components
 * with collapse/expand functionality and optional drag-to-resize
 */
import { useRef, useEffect, type ReactNode } from 'react';
import { usePanelState } from '../stores/usePanelState';
import './CollapsiblePanel.css';

interface CollapsiblePanelProps {
  id: string;
  category: 'leftOpen' | 'centerOpen' | 'rightOpen' | 'terminalOpen';
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  resizable?: boolean;
  resizeDirection?: 'horizontal' | 'vertical';
  minSize?: number; // Minimum size in pixels or percentage
  onResize?: (size: number) => void; // Called when resize ends
  className?: string;
}

export function CollapsiblePanel({
  id,
  category,
  title,
  children,
  defaultOpen = true,
  resizable = false,
  resizeDirection = 'vertical',
  minSize,
  onResize,
  className = '',
}: CollapsiblePanelProps) {
  const { state, setPanelOpen, setPanelSize } = usePanelState();
  const isOpen = category === 'terminalOpen'
    ? state.terminalOpen
    : (state[category] as any)[id] ?? defaultOpen;

  const resizeHandleRef = useRef<HTMLDivElement>(null);
  const isResizingRef = useRef(false);
  const startPosRef = useRef(0);
  const startSizeRef = useRef(0);

  const handleToggle = () => {
    setPanelOpen(category, id, !isOpen);
  };

  // Resize handle mouse handlers
  useEffect(() => {
    if (!resizable || !resizeHandleRef.current) return;

    const handle = resizeHandleRef.current;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      isResizingRef.current = true;
      startPosRef.current = resizeDirection === 'vertical' ? e.clientX : e.clientY;
      
      // Get current size from state
      let currentSize = 0;
      if (category === 'terminalOpen') {
        currentSize = state.sizes.terminalPct ?? 30;
      } else if (category === 'leftOpen') {
        currentSize = state.sizes.leftPx ?? 320;
      } else if (category === 'rightOpen') {
        currentSize = state.sizes.rightPx ?? 360;
      }
      startSizeRef.current = currentSize;

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = resizeDirection === 'vertical' ? 'col-resize' : 'row-resize';
      document.body.style.userSelect = 'none';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;

      const currentPos = resizeDirection === 'vertical' ? e.clientX : e.clientY;
      const delta = resizeDirection === 'vertical' 
        ? currentPos - startPosRef.current
        : startPosRef.current - currentPos; // Inverted for height (dragging up increases)

      let newSize = startSizeRef.current;
      
      if (category === 'terminalOpen') {
        // Terminal: percentage of viewport height
        const viewportHeight = window.innerHeight;
        const deltaPct = (delta / viewportHeight) * 100;
        newSize = Math.max(minSize ?? 10, Math.min(80, startSizeRef.current + deltaPct));
      } else if (category === 'leftOpen') {
        // Left column: pixels width
        newSize = Math.max(minSize ?? 200, Math.min(800, startSizeRef.current + delta));
      } else if (category === 'rightOpen') {
        // Right column: pixels width
        // For right column, dragging left decreases size, dragging right increases size
        newSize = Math.max(minSize ?? 240, Math.min(800, startSizeRef.current + delta));
      }

      // Update CSS variable immediately for smooth drag
      if (category === 'terminalOpen') {
        document.documentElement.style.setProperty('--terminal-height', `${newSize}%`);
      } else if (category === 'leftOpen') {
        document.documentElement.style.setProperty('--left-width', `${newSize}px`);
      } else if (category === 'rightOpen') {
        document.documentElement.style.setProperty('--right-width', `${newSize}px`);
      }
    };

    const handleMouseUp = () => {
      if (!isResizingRef.current) return;
      
      isResizingRef.current = false;
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';

      // Save to state
      const currentPos = resizeDirection === 'vertical' 
        ? (document.documentElement.style.getPropertyValue('--left-width') || document.documentElement.style.getPropertyValue('--right-width'))
        : document.documentElement.style.getPropertyValue('--terminal-height');
      
      if (currentPos) {
        let sizeValue = parseFloat(currentPos);
        if (category === 'terminalOpen') {
          setPanelSize('terminalPct', sizeValue);
        } else if (category === 'leftOpen') {
          setPanelSize('leftPx', sizeValue);
        } else if (category === 'rightOpen') {
          setPanelSize('rightPx', sizeValue);
        }
        onResize?.(sizeValue);
      }
    };

    handle.addEventListener('mousedown', handleMouseDown);

    return () => {
      handle.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizable, resizeDirection, category, state.sizes, minSize, setPanelSize, onResize]);

  return (
    <div className={`collapsible-panel ${className} ${!isOpen ? 'collapsed' : ''}`}>
      <div className="panel-header collapsible-panel-header">
        <div className="panel-header-title">{title}</div>
        <button
          className="panel-toggle-btn"
          onClick={handleToggle}
          aria-expanded={isOpen}
          aria-label={isOpen ? `Collapse ${title}` : `Expand ${title}`}
        >
          <span className={`chevron ${isOpen ? 'open' : 'closed'}`}>▼</span>
        </button>
      </div>
      <div 
        className="collapsible-panel-content"
        style={{ 
          maxHeight: isOpen ? '10000px' : '0',
          opacity: isOpen ? 1 : 0,
        }}
      >
        {/* Hide nested panel headers - CollapsiblePanel provides its own */}
        <div className="collapsible-panel-children">
          {children}
        </div>
      </div>
      {resizable && (
        <div
          ref={resizeHandleRef}
          className={`resize-handle resize-handle-${resizeDirection}`}
          aria-label={`Resize ${title}`}
        />
      )}
    </div>
  );
}

