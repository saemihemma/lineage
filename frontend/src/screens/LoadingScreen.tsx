/**
 * Loading Screen - Name input and loading animation
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadStateFromLocalStorage, saveStateToLocalStorage, createDefaultState } from '../utils/localStorage';
import './LoadingScreen.css';

const SELF_NAME_KEY = 'lineage_self_name';

export function LoadingScreen() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingComplete, setLoadingComplete] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingMessages] = useState([
    'Initializing systems...',
    'Calibrating clone matrices...',
    'Syncing with SELF network...',
    'Loading expedition protocols...',
    'Preparing resource harvesters...',
  ]);
  const [currentMessage, setCurrentMessage] = useState(loadingMessages[0]);

  // Load saved name from localStorage on mount
  useEffect(() => {
    const savedName = localStorage.getItem(SELF_NAME_KEY);
    if (savedName) {
      setName(savedName);
    }
  }, []);

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
    if (name.trim() && loadingComplete && !saving) {
      setSaving(true);
      try {
        const trimmedName = name.trim();
        console.log('🎯 LoadingScreen: Saving name and navigating to simulation', { name: trimmedName });

        // Save name to localStorage for future sessions
        localStorage.setItem(SELF_NAME_KEY, trimmedName);

        // Load current state from localStorage
        console.log('📥 LoadingScreen: Loading state from localStorage...');
        let currentState = loadStateFromLocalStorage();
        
        // If no state exists, create default
        if (!currentState) {
          console.log('📦 LoadingScreen: No saved state, creating new game state');
          currentState = createDefaultState();
        }
        
        console.log('📦 LoadingScreen: State loaded', {
          hasWombs: Array.isArray(currentState.wombs),
          wombCount: currentState.wombs?.length || 0,
          selfName: currentState.self_name,
          assemblerBuilt: currentState.assembler_built,
        });
        
        // Update self_name
        const updatedState = {
          ...currentState,
          self_name: trimmedName,
        };
        
        // Save to localStorage
        console.log('💾 LoadingScreen: Saving state with name to localStorage...');
        saveStateToLocalStorage(updatedState);
        
        // Navigate to simulation
        console.log('➡️ LoadingScreen: Navigating to simulation');
        navigate('/simulation');
      } catch (err) {
        console.error('❌ LoadingScreen: Failed to save name:', err);
        // Still navigate even if save fails (name will be lost)
        navigate('/simulation');
      } finally {
        setSaving(false);
      }
    }
  };

  const canEnter = name.trim().length > 0 && loadingComplete;

  // Check if the current name matches what's saved (only show "Welcome back" if names match)
  const savedName = localStorage.getItem(SELF_NAME_KEY);
  const isReturningUser = savedName !== null && savedName.trim() === name.trim();

  return (
    <div className="loading-screen">
      <div className="loading-content">
        <h2 className="loading-title">IDENTITY</h2>
        {isReturningUser && name && (
          <div style={{ color: '#00ff00', fontSize: '14px', marginBottom: '8px' }}>
            Welcome back, {name}
          </div>
        )}
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

