/**
 * Fuel Bar - Visual indicator of rate limit status
 */
import { useEffect, useState } from 'react';
import { limitsAPI, type LimitsStatus } from '../api/limits';
import './FuelBar.css';

export function FuelBar() {
  const [fuelStatus, setFuelStatus] = useState<LimitsStatus | null>(null);

  // Poll fuel status every 2-3 seconds
  // Gracefully handles failures - won't show errors if endpoint unavailable
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await limitsAPI.getStatus();
        if (status) {
          setFuelStatus(status);
        } else {
          // Endpoint not available - silently don't display fuel bar
          setFuelStatus(null);
        }
      } catch (err) {
        // Silently handle errors - don't show fuel bar if API unavailable
        // This prevents network error spam in console
        setFuelStatus(null);
      }
    };

    // Fetch immediately
    fetchStatus();

    // Then poll every 2.5 seconds
    const interval = setInterval(fetchStatus, 2500);

    return () => clearInterval(interval);
  }, []);

  // Don't render if endpoint not available
  if (!fuelStatus) {
    return null;
  }

  const combined = fuelStatus.endpoints.combined;
  const remaining = combined.remaining;
  const resetAt = combined.reset_at;
  const now = fuelStatus.now;
  const timeUntilReset = Math.max(0, resetAt - now);
  const minutesUntilReset = Math.floor(timeUntilReset / 60);
  const secondsUntilReset = timeUntilReset % 60;

  // Calculate percentage based on combined max actions per window
  // Combined max = gather(20) + grow(10) + expedition(10) + upload(10) = 50
  const maxActions = 50;
  const percentage = Math.min(100, (remaining / maxActions) * 100);

  // Color states
  let colorClass = 'fuel-ok';
  if (percentage < 20) {
    colorClass = 'fuel-low';
  } else if (percentage < 80) {
    colorClass = 'fuel-warn';
  }

  // Format time until reset
  const timeStr = timeUntilReset > 0
    ? `${minutesUntilReset}:${secondsUntilReset.toString().padStart(2, '0')}`
    : '0:00';

  return (
    <div className="fuel-bar-container">
      <div className="fuel-bar-label">Fuel</div>
      <div className="fuel-bar-wrapper">
        <div className={`fuel-bar ${colorClass}`}>
          <div
            className="fuel-bar-fill"
            style={{ width: `${percentage}%` }}
          />
          <div className="fuel-bar-ticks">
            {[0, 25, 50, 75, 100].map((tick) => (
              <div
                key={tick}
                className="fuel-bar-tick"
                style={{ left: `${tick}%` }}
              />
            ))}
          </div>
        </div>
        <div className="fuel-bar-text">
          {remaining > 0 ? (
            <span>{remaining} remaining</span>
          ) : (
            <span className="fuel-empty">Refuel in {timeStr}</span>
          )}
        </div>
      </div>
    </div>
  );
}

