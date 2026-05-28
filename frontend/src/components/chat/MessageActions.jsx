import React, { useState } from 'react';
import { Copy, Check, ThumbsUp, ThumbsDown, RotateCw, ChevronDown } from 'lucide-react';

/**
 * MessageActions — directly modeled after BeautifulUI's Streaming Text action bar (#streaming-text)
 * 
 * Features:
 * - Copy message to clipboard with instant checkmark feedback
 * - Thumbs Up / Down ratings
 * - Regenerate answer button
 * - Stacked sources avatar pill with source counter
 */
export default function MessageActions({ 
  text, 
  citations = [], 
  onRetry,
  onToggleSources,
  sourcesOpen = false 
}) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null); // 'like' | 'dislike' | null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  return (
    <div 
      className="bui-fade-up"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        marginTop: '8px',
        userSelect: 'none'
      }}
    >
      {/* Copy Button */}
      <button
        type="button"
        onClick={handleCopy}
        className="bui-icon-btn"
        title={copied ? "Copied!" : "Copy response"}
        aria-label="Copy response"
        style={{ color: copied ? 'var(--bui-green)' : 'var(--bui-ink-3)' }}
      >
        {copied ? <Check size={14} strokeWidth={2.5} /> : <Copy size={14} />}
      </button>

      {/* Thumbs Up */}
      <button
        type="button"
        onClick={() => setFeedback(feedback === 'like' ? null : 'like')}
        className={`bui-icon-btn ${feedback === 'like' ? 'active' : ''}`}
        title="Helpful grounded answer"
        aria-label="Like response"
        style={{ color: feedback === 'like' ? 'var(--bui-green)' : 'var(--bui-ink-3)' }}
      >
        <ThumbsUp size={14} />
      </button>

      {/* Thumbs Down */}
      <button
        type="button"
        onClick={() => setFeedback(feedback === 'dislike' ? null : 'dislike')}
        className={`bui-icon-btn ${feedback === 'dislike' ? 'active' : ''}`}
        title="Report inaccurate grounding"
        aria-label="Dislike response"
        style={{ color: feedback === 'dislike' ? 'var(--bui-rose)' : 'var(--bui-ink-3)' }}
      >
        <ThumbsDown size={14} />
      </button>

      {/* Retry / Regenerate */}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="bui-icon-btn"
          title="Regenerate grounded answer"
          aria-label="Regenerate"
        >
          <RotateCw size={14} />
        </button>
      )}

      {/* Grounding Sources Pill Button (BeautifulUI Sources Stack) */}
      {citations && citations.length > 0 && (
        <button
          type="button"
          onClick={onToggleSources}
          className="bui-btn bui-btn-ghost"
          style={{
            marginLeft: '8px',
            padding: '2px 8px',
            height: '24px',
            borderRadius: '6px',
            fontSize: '0.75rem',
            background: sourcesOpen ? 'var(--bui-hover-2)' : 'var(--bui-field)',
            border: '1px solid var(--bui-line)',
            color: sourcesOpen ? 'var(--bui-accent-cyan)' : 'var(--bui-ink-2)'
          }}
        >
          {/* Micro stacked avatar icons */}
          <span style={{ display: 'flex', marginLeft: '-2px', marginRight: '4px' }}>
            {citations.slice(0, 3).map((_, i) => (
              <span
                key={i}
                style={{
                  width: '14px',
                  height: '14px',
                  borderRadius: '50%',
                  background: i === 0 ? 'var(--bui-accent-cyan)' : i === 1 ? 'var(--bui-accent)' : 'var(--bui-green)',
                  marginLeft: i > 0 ? '-4px' : '0',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 0 1.5px var(--bui-canvas)',
                  fontSize: '8px',
                  color: '#fff',
                  fontWeight: 700
                }}
              >
                •
              </span>
            ))}
          </span>

          <span>{citations.length} sources</span>
          <ChevronDown 
            size={12} 
            style={{ 
              transition: 'transform 200ms ease',
              transform: sourcesOpen ? 'rotate(180deg)' : 'rotate(0deg)' 
            }} 
          />
        </button>
      )}
    </div>
  );
}
