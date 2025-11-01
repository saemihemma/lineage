/**
 * Loading Screen - Name input and loading animation
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './LoadingScreen.css';

export function LoadingScreen() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingComplete, setLoadingComplete] = useState(false);
  const [loadingMessages] = useState([
    'Initializing systems...',
    'Calibrating clone matrices...',
    'Syncing with SELF network...',
    'Loading expedition protocols...',
    'Preparing resource harvesters...',
  ]);
  const [currentMessage, setCurrentMessage] = useState(loadingMessages[0]);

  useEffect(() => {
    // Simulate loading progress
    const duration = 25000 + Math.random() * 5000; // 25-30 seconds
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(100, (elapsed / duration) * 100);
      setLoadingProgress(progress);

      // Update message periodically
      const messageIndex = Math.floor((progress / 100) * loadingMessages.length);
      if (messageIndex < loadingMessages.length) {
        setCurrentMessage(loadingMessages[messageIndex]);
      }

      if (progress >= 100) {
        setLoadingProgress(100);
        setLoadingComplete(true);
        setCurrentMessage('Ready');
        clearInterval(interval);
      }
    }, 50);

    return () => clearInterval(interval);
  }, [loadingMessages]);

  const handleEnter = () => {
    if (name.trim() && loadingComplete) {
      // TODO: Save name and navigate to simulation
      navigate('/simulation');
    }
  };

  const canEnter = name.trim().length > 0 && loadingComplete;

  return (
    <div className="loading-screen">
      <div className="loading-content">
        <h2 className="loading-title">IDENTITY</h2>
        <input
          type="text"
          className="loading-name-input"
          placeholder="Enter your SELF name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && canEnter && handleEnter()}
        />

        <button
          className="loading-enter-button"
          onClick={handleEnter}
          disabled={!canEnter}
        >
          ENTER SIMULATION
        </button>

        <div className="loading-progress-container">
          <div className="loading-progress-bar">
            <div
              className="loading-progress-fill"
              style={{ width: `${loadingProgress}%` }}
            />
          </div>
          <div className="loading-progress-text">{Math.round(loadingProgress)}%</div>
        </div>

        <div className="loading-message">{currentMessage}</div>
      </div>
    </div>
  );
}

