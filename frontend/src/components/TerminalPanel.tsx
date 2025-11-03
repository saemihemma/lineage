/**
 * Terminal Panel - displays log messages
 */
import { useEffect, useRef } from 'react';
import './TerminalPanel.css';

interface TerminalPanelProps {
  messages: string[];
}

export function TerminalPanel({ messages }: TerminalPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="panel terminal-panel">
      <div className="panel-header">Terminal / Tutorial</div>
      <div className="panel-content terminal-content">
        {messages.length === 0 ? (
          <div className="terminal-empty">No messages yet...</div>
        ) : (
          <div className="terminal-messages">
            {messages.map((message, index) => {
              const isFeralAttack = message.includes('FERAL DRONE ATTACK');
              const isTrinarySacrifice = message.includes('TRINARY SACRIFICE');
              const isRedMessage = isFeralAttack || isTrinarySacrifice;
              return (
                <div 
                  key={index} 
                  className={`terminal-message ${isRedMessage ? 'terminal-message-feral' : ''}`}
                >
                  {message.split('\n').map((line, lineIndex) => (
                    <div key={lineIndex}>{line}</div>
                  ))}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}

