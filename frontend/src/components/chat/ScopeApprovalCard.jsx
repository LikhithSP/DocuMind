import React, { useState } from 'react';
import { X } from 'lucide-react';

/**
 * ScopeApprovalCard — directly modeled after BeautifulUI's Approval Card primitive (#approval-card)
 * 
 * Provides an interactive human-in-the-loop card allowing users to tune retrieval
 * synthesis depth (Executive Summary, Exhaustive Evidence, Risk Audit) or input custom parameters.
 */
export default function ScopeApprovalCard({ onSelectMode, onDismiss }) {
  const [selectedOption, setSelectedOption] = useState('Executive Summary');

  const options = [
    { id: 'Executive Summary', label: 'Executive Summary (Key takeaways & bulleted metrics)' },
    { id: 'Exhaustive Evidence', label: 'Exhaustive Evidence (In-depth analysis with full passage quotes)' },
    { id: 'Compliance & Risk Audit', label: 'Compliance & Risk Audit (Focus on liabilities and exceptions)' }
  ];

  const handleContinue = () => {
    if (onSelectMode) onSelectMode(selectedOption);
  };

  return (
    <div 
      className="bui-fade-up bui-card"
      style={{
        width: '100%',
        maxWidth: '440px',
        padding: '16px 18px',
        margin: '12px 0',
        borderRadius: '16px',
        background: 'var(--bui-surface)',
        border: '1px solid var(--bui-line-strong)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
        position: 'relative'
      }}
    >
      {/* Dismiss Button */}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="bui-icon-btn"
          aria-label="Dismiss"
          style={{ position: 'absolute', top: '10px', right: '10px' }}
        >
          <X size={14} />
        </button>
      )}

      {/* Question Title */}
      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--bui-ink)', paddingRight: '24px' }}>
        How should DocuMind structure grounded answers?
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--bui-ink-3)', marginTop: '2px', marginBottom: '12px' }}>
        Select your preferred enterprise grounding format
      </div>

      {/* Menu / Option Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {options.map((opt) => {
          const isSelected = selectedOption === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => setSelectedOption(opt.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '8px 10px',
                borderRadius: '8px',
                background: isSelected ? 'rgba(255, 255, 255, 0.07)' : 'var(--bui-field)',
                border: isSelected ? '1px solid rgba(255, 255, 255, 0.18)' : '1px solid var(--bui-line)',
                color: isSelected ? '#ffffff' : 'var(--bui-ink-2)',
                textAlign: 'left',
                fontSize: '0.8125rem',
                cursor: 'pointer',
                transition: 'all 140ms ease',
                boxShadow: isSelected ? 'inset 0 1px 0 rgba(255, 255, 255, 0.06)' : 'none'
              }}
            >
              {/* Radio Circle */}
              <span style={{
                width: '15px',
                height: '15px',
                borderRadius: '50%',
                border: isSelected ? '2px solid #ffffff' : '1.5px solid var(--bui-ink-3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                {isSelected && (
                  <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#ffffff' }} />
                )}
              </span>

              <span>{opt.label}</span>
            </button>
          );
        })}
      </div>

      {/* Card Footer with Steps & Actions */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginTop: '14px',
        paddingTop: '10px',
        borderTop: '1px solid var(--bui-line)'
      }}>
        <span style={{
          fontSize: '0.72rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--bui-ink-3)'
        }}>
          1 / 1
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="bui-btn"
              style={{ padding: '4px 12px', fontSize: '0.75rem', borderRadius: '999px' }}
            >
              Skip
            </button>
          )}

          <button
            type="button"
            onClick={handleContinue}
            className="bui-btn bui-btn-primary"
            style={{ padding: '4px 14px', fontSize: '0.75rem', borderRadius: '999px' }}
          >
            Apply Format
          </button>
        </div>
      </div>
    </div>
  );
}
