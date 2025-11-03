/**
 * Panel state management with React Context and localStorage persistence
 * Manages panel open/closed state and panel sizes for Mission Control UI
 */
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

const STORAGE_KEY = 'lineage:ui:v1';

export interface PanelState {
  leftOpen: {
    ftue: boolean;
    resources: boolean;
  };
  centerOpen: {
    womb: boolean;
    clones: boolean;
    expeditions: boolean;
  };
  rightOpen: {
    cloneDetails: boolean;
    progress: boolean;
    self: boolean;
  };
  terminalOpen: boolean;
  sizes: {
    leftPx?: number;      // Left column width in pixels (default: 320px)
    rightPx?: number;     // Right column width in pixels (default: 360px)
    terminalPct?: number; // Terminal height as % of viewport (default: 30%)
  };
}

const DEFAULT_STATE: PanelState = {
  leftOpen: {
    ftue: true,      // Expanded until done
    resources: false, // Collapsed by default
  },
  centerOpen: {
    womb: true,
    clones: true,
    expeditions: true,
  },
  rightOpen: {
    cloneDetails: true,  // Expanded if clone selected, else shows "Select a clone"
    progress: false,     // Collapsed (auto-expands when task starts)
    self: true,
  },
  terminalOpen: true,
  sizes: {
    leftPx: 320,
    rightPx: 360,
    terminalPct: 30,
  },
};

interface PanelStateContextType {
  state: PanelState;
  togglePanel: (category: 'leftOpen' | 'centerOpen' | 'rightOpen' | 'terminalOpen', id: string) => void;
  setPanelOpen: (category: 'leftOpen' | 'centerOpen' | 'rightOpen' | 'terminalOpen', id: string, open: boolean) => void;
  setPanelSize: (sizeKey: 'leftPx' | 'rightPx' | 'terminalPct', size: number) => void;
  resetToDefaults: () => void;
}

const PanelStateContext = createContext<PanelStateContextType | undefined>(undefined);

export function PanelStateProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PanelState>(() => {
    // Load from localStorage on mount (synchronous operation)
    try {
      // Defensive check: localStorage may not be available (SSR, private browsing)
      if (typeof window === 'undefined' || !window.localStorage) {
        console.warn('localStorage not available, using default state');
        return DEFAULT_STATE;
      }

      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Merge with defaults to handle schema changes
        // Ensure sizes object always exists with valid structure
        const mergedState = {
          ...DEFAULT_STATE,
          ...parsed,
          leftOpen: { ...DEFAULT_STATE.leftOpen, ...(parsed.leftOpen || {}) },
          centerOpen: { ...DEFAULT_STATE.centerOpen, ...(parsed.centerOpen || {}) },
          rightOpen: { ...DEFAULT_STATE.rightOpen, ...(parsed.rightOpen || {}) },
          sizes: {
            ...DEFAULT_STATE.sizes,
            ...(parsed.sizes || {}),
          },
        };
        // Validate sizes are numbers
        if (typeof mergedState.sizes.leftPx !== 'number') mergedState.sizes.leftPx = DEFAULT_STATE.sizes.leftPx;
        if (typeof mergedState.sizes.rightPx !== 'number') mergedState.sizes.rightPx = DEFAULT_STATE.sizes.rightPx;
        if (typeof mergedState.sizes.terminalPct !== 'number') mergedState.sizes.terminalPct = DEFAULT_STATE.sizes.terminalPct;
        return mergedState;
      }
    } catch (err) {
      console.warn('Failed to load panel state from localStorage:', err);
    }
    // Always return a valid state object
    return DEFAULT_STATE;
  });

  // Save to localStorage whenever state changes
  useEffect(() => {
    try {
      // Defensive check: localStorage may not be available
      if (typeof window === 'undefined' || !window.localStorage) {
        return;
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (err) {
      console.warn('Failed to save panel state to localStorage:', err);
    }
  }, [state]);

  const togglePanel = useCallback((category: 'leftOpen' | 'centerOpen' | 'rightOpen' | 'terminalOpen', id: string) => {
    setState((prev) => {
      if (category === 'terminalOpen') {
        return { ...prev, terminalOpen: !prev.terminalOpen };
      }
      return {
        ...prev,
        [category]: {
          ...prev[category],
          [id]: !(prev[category] as any)[id],
        },
      };
    });
  }, []);

  const setPanelOpen = useCallback((category: 'leftOpen' | 'centerOpen' | 'rightOpen' | 'terminalOpen', id: string, open: boolean) => {
    setState((prev) => {
      if (category === 'terminalOpen') {
        return { ...prev, terminalOpen: open };
      }
      return {
        ...prev,
        [category]: {
          ...prev[category],
          [id]: open,
        },
      };
    });
  }, []);

  const setPanelSize = useCallback((sizeKey: 'leftPx' | 'rightPx' | 'terminalPct', size: number) => {
    setState((prev) => ({
      ...prev,
      sizes: {
        ...prev.sizes,
        [sizeKey]: size,
      },
    }));
  }, []);

  const resetToDefaults = useCallback(() => {
    setState(DEFAULT_STATE);
  }, []);

  return (
    <PanelStateContext.Provider value={{ state, togglePanel, setPanelOpen, setPanelSize, resetToDefaults }}>
      {children}
    </PanelStateContext.Provider>
  );
}

export function usePanelState() {
  const context = useContext(PanelStateContext);
  if (!context) {
    throw new Error('usePanelState must be used within PanelStateProvider');
  }
  return context;
}

