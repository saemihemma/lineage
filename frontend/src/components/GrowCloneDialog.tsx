/**
 * Grow Clone Dialog - select clone type to grow
 */
import { useState } from 'react';
import './GrowCloneDialog.css';

interface GrowCloneDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGrow: (kind: string) => void;
  disabled: boolean;
}

const CLONE_TYPES = {
  BASIC: 'Basic Clone',
  MINER: 'Mining Clone',
  VOLATILE: 'Volatile Clone',
};

export function GrowCloneDialog({ isOpen, onClose, onGrow, disabled }: GrowCloneDialogProps) {
  const [selectedKind, setSelectedKind] = useState<string>('BASIC');

  if (!isOpen) return null;

  const handleGrow = () => {
    onGrow(selectedKind);
    onClose();
  };

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
        <h3 className="dialog-title">Grow Clone</h3>
        <p className="dialog-subtitle">Select clone type to grow:</p>
        
        <div className="clone-type-options">
          {Object.entries(CLONE_TYPES).map(([kind, display]) => (
            <label key={kind} className="clone-type-option">
              <input
                type="radio"
                name="cloneType"
                value={kind}
                checked={selectedKind === kind}
                onChange={(e) => setSelectedKind(e.target.value)}
              />
              <span>{display}</span>
            </label>
          ))}
        </div>

        <div className="dialog-actions">
          <button className="dialog-btn cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            className="dialog-btn grow"
            onClick={handleGrow}
            disabled={disabled}
          >
            Grow {CLONE_TYPES[selectedKind as keyof typeof CLONE_TYPES]}
          </button>
        </div>
      </div>
    </div>
  );
}

