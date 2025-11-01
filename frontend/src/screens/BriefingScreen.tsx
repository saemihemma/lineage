/**
 * Briefing Screen - First screen players see
 * Displays game introduction and instructions
 */
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import './BriefingScreen.css';

interface BriefingData {
  header: string;
  subheader: string;
  body: string[];
  bold_lines: string[];
}

export function BriefingScreen() {
  const navigate = useNavigate();
  const [briefingData, setBriefingData] = useState<BriefingData | null>(null);

  useEffect(() => {
    // Load briefing text from JSON
    fetch('/data/briefing_text.json')
      .then((res) => res.json())
      .then((data) => setBriefingData(data))
      .catch((err) => {
        console.error('Failed to load briefing text:', err);
        // Fallback data
        setBriefingData({
          header: 'LINEAGE PROTOCOL — FIELD BRIEFING',
          subheader: 'Prototype simulation of clone and character progression in EVE Frontier.',
          body: [],
          bold_lines: [],
        });
      });
  }, []);

  const handleNext = () => {
    navigate('/loading');
  };

  if (!briefingData) {
    return (
      <div className="briefing-screen loading">
        <div>Loading briefing...</div>
      </div>
    );
  }

  return (
    <div className="briefing-screen">
      <div className="briefing-content">
        <h1 className="briefing-header">{briefingData.header}</h1>
        <p className="briefing-subheader">{briefingData.subheader}</p>
        
        <div className="briefing-body">
          {briefingData.body.map((line, index) => {
            const isBold = briefingData.bold_lines.includes(line.trim());
            const stepNumber = isBold
              ? briefingData.bold_lines.indexOf(line.trim()) + 1
              : null;
            
            return (
              <p
                key={index}
                className={isBold ? 'briefing-bold' : 'briefing-text'}
              >
                {stepNumber && `${stepNumber}. `}
                {line}
              </p>
            );
          })}
        </div>
      </div>
      
      <button className="briefing-next-button" onClick={handleNext}>
        NEXT
      </button>
    </div>
  );
}

