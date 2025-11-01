/**
 * Gather Panel - resource gathering buttons
 */
import './GatherPanel.css';

interface GatherPanelProps {
  onGather: (resource: string) => void;
  disabled: boolean;
}

const RESOURCES = ['Tritanium', 'Metal Ore', 'Biomass', 'Synthetic', 'Organic', 'Shilajit'];

export function GatherPanel({ onGather, disabled }: GatherPanelProps) {
  return (
    <div className="panel gather-panel">
      <div className="panel-header">Gather Resources</div>
      <div className="panel-content">
        <div className="gather-buttons">
          {RESOURCES.map((resource) => (
            <button
              key={resource}
              className="gather-btn"
              onClick={() => onGather(resource)}
              disabled={disabled}
            >
              Gather {resource}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

