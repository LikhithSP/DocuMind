import React, { useState, useEffect } from 'react';

/**
 * PixelLoader — directly modeled after BeautifulUI's Loading State primitive (#loading-state)
 * Features:
 * - 3x3 pixel grid with staggered pulse animations
 * - Animated gradient shimmer status label
 * - High-precision elapsed time counter
 */
export default function PixelLoader({ label = "Synthesizing answer", startTime = null }) {
  const [elapsed, setElapsed] = useState("0.0s");

  useEffect(() => {
    const start = startTime || Date.now();
    const timer = setInterval(() => {
      const diff = ((Date.now() - start) / 1000).toFixed(1);
      setElapsed(`${diff}s`);
    }, 100);
    return () => clearInterval(timer);
  }, [startTime]);

  // 3x3 pixel grid layout with staggered animation delays
  const pixelDelays = [
    [90, 180, 270],
    [0, 90, 180],
    [90, 180, 270]
  ];

  return (
    <div 
      role="status" 
      className="bui-fade-up"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '12px',
        padding: '8px 14px',
        borderRadius: '999px',
        background: 'var(--bui-field)',
        border: '1px solid var(--bui-line)',
        backdropFilter: 'blur(8px)',
        boxShadow: 'var(--bui-shadow-btn)'
      }}
    >
      {/* 3x3 Pixel Matrix */}
      <span 
        aria-hidden="true" 
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 4px)',
          gap: '2px',
          flexShrink: 0
        }}
      >
        {pixelDelays.flat().map((delay, idx) => (
          <span
            key={idx}
            style={{
              width: '4px',
              height: '4px',
              borderRadius: '1px',
              backgroundColor: 'var(--bui-ink)',
              animation: `bui-pixel-on 700ms ease-in-out ${delay}ms infinite`
            }}
          />
        ))}
      </span>

      {/* Shimmering Text Status */}
      <span 
        className="bui-shimmer-text" 
        style={{
          fontSize: '0.8125rem',
          fontWeight: 600,
          letterSpacing: '-0.01em'
        }}
      >
        {label}
      </span>

      {/* Monospace Elapsed Seconds Counter */}
      <span 
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
          color: 'var(--bui-ink-3)',
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.02em',
          paddingLeft: '4px',
          borderLeft: '1px solid var(--bui-line)'
        }}
      >
        {elapsed}
      </span>
    </div>
  );
}
