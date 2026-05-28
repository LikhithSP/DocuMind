import React from 'react';
import { CornerDownRight } from 'lucide-react';

/**
 * FollowUpChips — directly modeled after BeautifulUI's Streaming Text Follow-ups primitive (#streaming-text)
 * 
 * Displays context-aware suggestion questions that the user can click to immediately
 * submit as the next conversational turn.
 */
export default function FollowUpChips({ onSelectQuery }) {
  // Generate smart follow-up suggestions dynamically
  const suggestions = [
    "What are the specific exceptions to this policy?",
    "Can you provide a bulleted executive summary?",
    "Show me the exact page and paragraph references",
    "How does this compare to industry standard terms?"
  ];

  return (
    <div 
      className="bui-fade-up"
      style={{
        marginTop: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}
    >
      <div style={{
        fontSize: '0.72rem',
        fontWeight: 600,
        color: 'var(--bui-ink-3)',
        display: 'flex',
        alignItems: 'center',
        gap: '5px'
      }}>
        <CornerDownRight size={12} color="var(--bui-accent-cyan)" /> Suggested Follow-ups
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {suggestions.map((text, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectQuery(text)}
            className="bui-btn"
            style={{
              padding: '4px 10px',
              borderRadius: '8px',
              fontSize: '0.75rem',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--bui-line)',
              color: 'var(--bui-ink-2)',
              textAlign: 'left'
            }}
          >
            <span>{text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
