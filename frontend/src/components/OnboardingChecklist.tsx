/**
 * Onboarding Checklist - Persistent guide for new players
 */
import { useState } from 'react';
import type { GameState } from '../types/game';
import './OnboardingChecklist.css';

interface OnboardingChecklistProps {
  state: GameState;
}

interface FTUEState {
  step_gather_10_tritanium?: boolean;
  step_build_womb?: boolean;
  step_grow_clone?: boolean;
  step_first_expedition?: boolean;
  step_upload_clone?: boolean;
}

export function OnboardingChecklist({ state }: OnboardingChecklistProps) {
  // Extract FTUE flags from state (gracefully handle missing ftue object)
  const ftue: FTUEState = (state as any).ftue || {};
  const [collapsed, setCollapsed] = useState(false);

  // Define steps with completion checks
  const steps = [
    {
      id: 'gather_10_tritanium',
      label: 'Gather 10 Tritanium',
      completed: ftue.step_gather_10_tritanium || false,
      check: () => {
        const tritanium = state.resources?.Tritanium || 0;
        return tritanium >= 10;
      },
    },
    {
      id: 'build_womb',
      label: 'Build Womb',
      completed: ftue.step_build_womb || false,
      check: () => {
        // Use wombs array if available, fallback to assembler_built
        if (state.wombs && state.wombs.length > 0) {
          return state.wombs.some(w => w.durability > 0);
        }
        return state.assembler_built || false;
      },
    },
    {
      id: 'grow_clone',
      label: 'Grow your first clone',
      completed: ftue.step_grow_clone || false,
      check: () => {
        const clones = state.clones || {};
        return Object.keys(clones).length > 0;
      },
    },
    {
      id: 'first_expedition',
      label: 'Go on your first expedition',
      completed: ftue.step_first_expedition || false,
      check: () => {
        // Check if any clone has XP from expeditions
        const clones = state.clones || {};
        return Object.values(clones).some((clone: any) => {
          const xp = clone.xp || {};
          // Backend uses uppercase keys: MINING, COMBAT, EXPLORATION
          return (xp.MINING || 0) + (xp.COMBAT || 0) + (xp.EXPLORATION || 0) > 0;
        });
      },
    },
    {
      id: 'upload_clone',
      label: 'Upload a clone to SELF',
      completed: ftue.step_upload_clone || false,
      check: () => {
        // Check if any clone is uploaded
        const clones = state.clones || {};
        return Object.values(clones).some((clone: any) => clone.uploaded === true);
      },
    },
  ];

  // Determine current step (first incomplete)
  const currentStepIndex = steps.findIndex((step) => {
    const isCompleted = step.completed || step.check();
    return !isCompleted;
  });

  const allCompleted = currentStepIndex === -1;

  // Always show the checklist, even when all steps are completed
  // Users should be able to see what they've accomplished
  const currentStep = currentStepIndex >= 0 ? steps[currentStepIndex] : null;

  return (
    <div className={`onboarding-checklist ${collapsed ? 'collapsed' : ''}`}>
      <div className="checklist-header" onClick={() => setCollapsed(!collapsed)}>
        <div className="checklist-title">
          <span className="checklist-icon">📋</span>
          <span>Getting Started</span>
        </div>
        <div className="checklist-toggle">{collapsed ? '▶' : '▼'}</div>
      </div>

      {!collapsed && (
        <div className="checklist-content">
          <div className="checklist-steps">
            {steps.map((step, index) => {
              const isCompleted = step.completed || step.check();
              const isCurrent = index === currentStepIndex;
              const stepClass = isCompleted
                ? 'step-completed'
                : isCurrent
                ? 'step-current'
                : 'step-pending';

              return (
                <div key={step.id} className={`checklist-step ${stepClass}`}>
                  <div className="step-indicator">
                    {isCompleted ? '✓' : isCurrent ? '→' : '○'}
                  </div>
                  <div className="step-label">{step.label}</div>
                </div>
              );
            })}
          </div>

          {currentStep && (
            <div className="checklist-hint">
              <strong>After that:</strong> Level your SELF
            </div>
          )}
        </div>
        )}
    </div>
  );
}

