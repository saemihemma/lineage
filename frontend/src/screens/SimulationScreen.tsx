/**
 * Simulation Screen - Main game interface
 * This will be the most complex screen to convert
 */
import { useEffect, useState } from 'react';
import './SimulationScreen.css';

export function SimulationScreen() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Load game state from API
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="simulation-screen">
        <div>Loading simulation...</div>
      </div>
    );
  }

  return (
    <div className="simulation-screen">
      <div className="simulation-header">
        <h1>LINEAGE</h1>
        <div className="simulation-stats">SELF Level: 1 | Soul: 100%</div>
      </div>
      
      <div className="simulation-content">
        <p>Simulation screen - Coming soon</p>
        <p>This will be converted from the Tkinter version</p>
      </div>
    </div>
  );
}

