/**
 * Resources Panel - displays current resources
 */
import './Panel.css';
import './ResourcesPanel.css';

interface ResourcesPanelProps {
  resources: Record<string, number>;
}

export function ResourcesPanel({ resources }: ResourcesPanelProps) {
  const resourceOrder = ['Tritanium', 'Metal Ore', 'Biomass', 'Synthetic', 'Organic', 'Shilajit'];

  return (
    <div className="panel resources-panel">
      <div className="panel-header">Resources</div>
      <div className="panel-content">
        {resourceOrder.map((resource) => (
          <div key={resource} className="resource-item">
            <span className="resource-name">{resource}:</span>
            <span className="resource-amount">{resources[resource] || 0}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

