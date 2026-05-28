import React, { useState } from 'react';
import { ChevronDown, Bookmark } from 'lucide-react';

/**
 * SourceContextCards — directly modeled after BeautifulUI's Context Cards primitive (#context-cards)
 * 
 * Renders grounded knowledge chunks with clean card aesthetics, page markers, 
 * cross-encoder score badges, and readable quote snippets.
 */
export default function SourceContextCards({ citations = [] }) {
  const [expandedIndices, setExpandedIndices] = useState({});

  if (!citations || citations.length === 0) return null;

  const toggleExpand = (idx) => {
    setExpandedIndices(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div 
      className="bui-fade-up"
      style={{
        marginTop: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}
    >
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 2px' }}>
        <div style={{
          fontSize: '0.72rem',
          fontWeight: 700,
          color: 'var(--bui-accent-cyan)',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <Bookmark size={13} /> Grounding Evidence Chunks
        </div>
        <span style={{
          fontSize: '0.6875rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--bui-ink-3)',
          background: 'var(--bui-field)',
          padding: '1px 6px',
          borderRadius: '4px',
          border: '1px solid var(--bui-line)'
        }}>
          {citations.length} retrieved
        </span>
      </div>

      {/* Cards Grid / Stack */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {citations.map((c, idx) => {
          const rawName = c.document || "Document";
          const displayName = rawName.length > 44 ? rawName.slice(0, 41) + "..." : rawName;
          const isHighRelevance = (c.rerank_score !== undefined && c.rerank_score > -5.0) || (c.score && c.score > 0.6);
          const isExpanded = !!expandedIndices[idx];

          const fileExt = rawName.split('.').pop()?.toUpperCase() || 'DOC';
          const badgeBg = fileExt === 'PDF' ? '#ef4444' : fileExt === 'DOCX' ? '#78716c' : '#10b981';

          return (
            <div
              key={idx}
              className="bui-card"
              style={{
                borderRadius: '12px',
                padding: '10px 14px',
                background: 'var(--bui-surface)',
                border: '1px solid var(--bui-line)',
                boxShadow: '0 2px 10px rgba(0, 0, 0, 0.25)',
                transition: 'border-color 150ms ease, transform 150ms ease'
              }}
            >
              {/* Card Title Row */}
              <div 
                onClick={() => toggleExpand(idx)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  userSelect: 'none',
                  gap: '10px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  {/* File Type Pill */}
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '2px 5px',
                    borderRadius: '4px',
                    background: badgeBg,
                    color: '#fff',
                    flexShrink: 0,
                    letterSpacing: '0.02em'
                  }}>
                    {fileExt}
                  </span>

                  <span style={{
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    color: 'var(--bui-ink)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {displayName}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                  {/* Page & Chunk Indicator */}
                  <span style={{
                    fontSize: '0.6875rem',
                    color: 'var(--bui-ink-3)',
                    fontFamily: 'var(--font-mono)'
                  }}>
                    p.{c.page}
                  </span>

                  {/* High Match / Corroborating Tag */}
                  <span style={{
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '999px',
                    background: isHighRelevance ? 'var(--bui-green-tint)' : 'rgba(217, 119, 87, 0.12)',
                    color: isHighRelevance ? 'var(--bui-green)' : 'var(--bui-accent)',
                    border: `1px solid ${isHighRelevance ? 'rgba(16, 185, 129, 0.3)' : 'rgba(217, 119, 87, 0.28)'}`
                  }}>
                    {isHighRelevance ? 'High Match' : 'Corroborating'}
                  </span>

                  <ChevronDown 
                    size={14} 
                    style={{
                      transition: 'transform 200ms cubic-bezier(0.23, 1, 0.32, 1)',
                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                      color: 'var(--bui-ink-3)'
                    }} 
                  />
                </div>
              </div>

              {/* Quote Snippet Body */}
              <div 
                style={{
                  marginTop: '8px',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  background: 'var(--bui-inset)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  fontSize: '0.8rem',
                  lineHeight: 1.5,
                  color: 'var(--bui-ink-2)'
                }}
              >
                <div style={{ fontStyle: 'italic' }}>
                  "{isExpanded ? c.snippet : (c.snippet?.length > 160 ? c.snippet.slice(0, 160) + '...' : c.snippet)}"
                </div>

                {/* Technical fusion telemetry */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  marginTop: '6px',
                  paddingTop: '6px',
                  borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                  fontSize: '0.6875rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--bui-ink-3)'
                }}>
                  {c.rerank_score !== undefined && (
                    <span>Re-rank: <strong style={{ color: 'var(--bui-accent-cyan)' }}>{c.rerank_score}</strong></span>
                  )}
                  {c.rrf_score !== undefined && (
                    <span>RRF: <strong style={{ color: 'var(--bui-ink-2)' }}>{c.rrf_score}</strong></span>
                  )}
                  {c.chunk_id && (
                    <span style={{ marginLeft: 'auto', opacity: 0.7 }}>ID: {c.chunk_id}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
