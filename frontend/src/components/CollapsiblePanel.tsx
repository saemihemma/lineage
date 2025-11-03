/**
 * CollapsiblePanel - Wrapper component that enhances existing .panel components
 * with collapse/expand functionality
 */
import type { ReactNode } from 'react';
import { usePanelState } from '../stores/usePanelState';
import './CollapsiblePanel.css';

interface CollapsiblePanelProps {
  id: string;
  category: 'leftOpen' | 'centerOpen' | 'rightOpen' | 'bottomLeftOpen' | 'bottomRightOpen' | 'terminalOpen';
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}

export function CollapsiblePanel({
  id,
  category,
  title,
  children,
  defaultOpen = true,
  className = '',
}: CollapsiblePanelProps) {
  const { state, setPanelOpen } = usePanelState();
  const isOpen = category === 'terminalOpen'
    ? state.terminalOpen
    : (state[category] as any)[id] ?? defaultOpen;

  const handleToggle = () => {
    setPanelOpen(category, id, !isOpen);
  };

  return (
    <div id={id} className={`collapsible-panel ${className} ${!isOpen ? 'collapsed' : ''}`}>
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
    </div>
  );
}

