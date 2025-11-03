/**
 * MissionControlLayout - CSS Grid wrapper for Mission Control dashboard
 * Fixed layout with no resize functionality
 */
import type { ReactNode } from 'react';
import './MissionControlLayout.css';

interface MissionControlLayoutProps {
  children: ReactNode;
  topHud: ReactNode;
}

export function MissionControlLayout({ children, topHud }: MissionControlLayoutProps) {
  return (
    <div className="mission-control-layout">
      <div className="mission-control-hud">
        {topHud}
      </div>
      <div className="mission-control-grid">
        {children}
      </div>
    </div>
  );
}

