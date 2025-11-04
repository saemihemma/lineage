/**
 * Grow Clone Dialog - select clone type to grow
 */
import { useState, useEffect } from 'react';
import type { GameState } from '../types/game';
import { isCloneTypeUnlocked, getCloneUnlockRequirement } from '../utils/wombs';
import './GrowCloneDialog.css';

interface GrowCloneDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGrow: (kind: string) => void;
  disabled: boolean;
  state: GameState | null;
}

const CLONE_TYPES = {
  BASIC: 'Basic Clone',
  MINER: 'Mining Clone',
  VOLATILE: 'Volatile Clone',
};

export function GrowCloneDialog({ isOpen, onClose, onGrow, disabled, state }: GrowCloneDialogProps) {
  const [selectedKind, setSelectedKind] = useState<string>('BASIC');

  // Reset to BASIC when dialog opens if BASIC is the only available option
  useEffect(() => {
    if (isOpen && state) {
      const basicUnlocked = isCloneTypeUnlocked(state, 'BASIC');
      if (!basicUnlocked) {
        // Shouldn't happen, but fallback
        setSelectedKind('BASIC');
      } else {
        // If current selection is locked, reset to BASIC
        const currentUnlocked = isCloneTypeUnlocked(state, selectedKind);
        if (!currentUnlocked) {
          setSelectedKind('BASIC');
        }
      }
    }
  }, [isOpen, state, selectedKind]);

  if (!isOpen) return null;

  const handleGrow = () => {
    // Double-check unlock status before growing
    if (state && !isCloneTypeUnlocked(state, selectedKind)) {
      return; // Shouldn't reach here if UI is correct
    }
    onGrow(selectedKind);
    onClose();
  };

  const isSelectedUnlocked = state ? isCloneTypeUnlocked(state, selectedKind) : true;

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
        <h3 className="dialog-title">Grow Clone</h3>
        <p className="dialog-subtitle">Select clone type to grow:</p>
        
        <div className="clone-type-options">
          {Object.entries(CLONE_TYPES).map(([kind, display]) => {
            const isUnlocked = state ? isCloneTypeUnlocked(state, kind) : true;
            const requirement = getCloneUnlockRequirement(kind);
            
            return (
              <label 
                key={kind} 
                className={`clone-type-option ${!isUnlocked ? 'disabled' : ''}`}
              >
                <input
                  type="radio"
                  name="cloneType"
                  value={kind}
                  checked={selectedKind === kind}
                  onChange={(e) => {
                    // Only allow selection if unlocked
                    if (isUnlocked) {
                      setSelectedKind(e.target.value);
                    }
                  }}
                  disabled={!isUnlocked}
                />
                <span className={!isUnlocked ? 'disabled-text' : ''}>
                  {display}
                  {!isUnlocked && requirement && (
                    <span className="unlock-requirement"> ({requirement})</span>
                  )}
                </span>
              </label>
            );
          })}
        </div>

        <div className="dialog-actions">
          <button className="dialog-btn cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            className="dialog-btn grow"
            onClick={handleGrow}
            disabled={disabled || !isSelectedUnlocked}
          >
            Grow {CLONE_TYPES[selectedKind as keyof typeof CLONE_TYPES]}
          </button>
        </div>
      </div>
    </div>
  );
}

