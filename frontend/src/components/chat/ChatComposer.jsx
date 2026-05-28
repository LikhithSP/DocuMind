import React, { useState, useRef, useEffect } from 'react';
import { 
  ArrowUp, Mic, Square, Cpu, Paperclip
} from 'lucide-react';

/**
 * ChatComposer — directly modeled after BeautifulUI's Prompt Bar primitive (#prompt-bar)
 * and Chat Composer (#chat-composer).
 * 
 * Features:
 * - Floating rounded composer shell with hairline border & focus glow
 * - Auto-expanding multi-line textarea
 * - Integrated real-time Web Speech voice input
 * - Model selector pill & Top-K density controls
 * - Dynamic Send / Stop streaming button with micro-animations
 */
export default function ChatComposer({ 
  queryInput, 
  setQueryInput, 
  onSend, 
  onStop, 
  isQuerying,
  hasDocuments = true,
  onOpenDocuments
}) {
  const textareaRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState('Hybrid RAG v2');
  const [topK, setTopK] = useState(5);
  const [showConfig, setShowConfig] = useState(false);

  // Voice Input SpeechRecognition state
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);
  const baseTextRef = useRef('');
  const silenceTimerRef = useRef(null);

  const clearSilenceTimer = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      clearSilenceTimer();
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const toggleVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
      return;
    }

    if (isListening) {
      clearSilenceTimer();
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      // Setting continuous to false allows browser speech engine to auto-stop on silence
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      baseTextRef.current = queryInput.trim();

      recognition.onstart = () => {
        setIsListening(true);
        clearSilenceTimer();
        // Auto-stop after 5s if user clicks mic but never speaks
        silenceTimerRef.current = setTimeout(() => {
          recognitionRef.current?.stop();
        }, 5000);
      };

      recognition.onresult = (event) => {
        clearSilenceTimer();
        let fullTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript;
        }
        const base = baseTextRef.current;
        const combined = base ? `${base} ${fullTranscript.trim()}` : fullTranscript.trim();
        setQueryInput(combined);

        // Auto-stop 1.5 seconds after the user stops speaking
        silenceTimerRef.current = setTimeout(() => {
          recognitionRef.current?.stop();
        }, 1500);
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        clearSilenceTimer();
        setIsListening(false);
      };

      recognition.onend = () => {
        clearSilenceTimer();
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      clearSilenceTimer();
      setIsListening(false);
    }
  };

  // Auto-resize textarea height based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [queryInput]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (queryInput.trim() && !isQuerying) {
        if (isListening) {
          recognitionRef.current?.stop();
          setIsListening(false);
        }
        onSend();
      }
    }
  };

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '10px' }}>

      {/* Main Composer Box */}
      <div 
        className="bui-card"
        style={{
          borderRadius: '16px',
          padding: '10px 14px',
          background: 'var(--bui-surface)',
          border: '1px solid var(--bui-line-strong)',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          transition: 'border-color 150ms ease, box-shadow 150ms ease'
        }}
      >
        {/* Top / Input Row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
          <textarea
            ref={textareaRef}
            rows={1}
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDocuments 
                ? "Ask anything grounded strictly in your documents... (Press Enter to query)"
                : "Upload a document above to start grounded enterprise Q&A..."
            }
            disabled={isQuerying}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--bui-ink)',
              fontSize: '0.9375rem',
              lineHeight: '1.5',
              resize: 'none',
              minHeight: '44px',
              maxHeight: '160px',
              fontFamily: 'inherit',
              padding: '6px 2px'
            }}
          />
        </div>

        {/* Bottom Metadata & Controls Bar */}
        <div 
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px',
            paddingTop: '6px',
            borderTop: '1px solid var(--bui-line)',
            marginTop: '2px'
          }}
        >
          {/* Left Controls: Model & RAG Settings */}
          <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
            <button
              type="button"
              onClick={() => setShowConfig(!showConfig)}
              className="bui-pill"
              title="Pipeline Configuration"
              style={{
                fontSize: '0.72rem',
                gap: '5px'
              }}
            >
              <Cpu size={12} color="var(--bui-accent)" />
              <span>{selectedModel}</span>
              <span style={{ opacity: 0.5 }}>•</span>
              <span>Top {topK}</span>
            </button>

            {showConfig && (
              <div 
                className="bui-fade-up" 
                style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '8px', 
                  background: 'var(--bui-field)',
                  padding: '2px 8px',
                  borderRadius: '6px',
                  border: '1px solid var(--bui-line)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {['Hybrid RAG v2', 'Groq Llama 3.3'].map(mName => (
                    <button
                      key={mName}
                      type="button"
                      onClick={() => setSelectedModel(mName)}
                      style={{
                        border: 'none',
                        background: selectedModel === mName ? 'rgba(255,255,255,0.1)' : 'transparent',
                        color: selectedModel === mName ? '#fff' : 'var(--bui-ink-3)',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {mName}
                    </button>
                  ))}
                </div>

                <span style={{ color: 'var(--bui-line-strong)' }}>|</span>

                <span style={{ fontSize: '0.68rem', color: 'var(--bui-ink-3)' }}>k:</span>
                {[3, 5, 8].map(kVal => (
                  <button
                    key={kVal}
                    type="button"
                    onClick={() => setTopK(kVal)}
                    style={{
                      border: 'none',
                      background: topK === kVal ? 'rgba(255,255,255,0.1)' : 'transparent',
                      color: topK === kVal ? '#fff' : 'var(--bui-ink-2)',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    {kVal}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right Controls: Actions & Send Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {/* Real-time Listening Badge */}
            {isListening && (
              <span 
                className="bui-fade-up"
                style={{ 
                  fontSize: '0.72rem', 
                  color: '#f43f5e', 
                  fontWeight: 600, 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '5px',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  background: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.3)'
                }}
              >
                <span style={{ 
                  width: '6px', 
                  height: '6px', 
                  borderRadius: '50%', 
                  background: '#f43f5e', 
                  display: 'inline-block',
                  boxShadow: '0 0 6px #f43f5e'
                }} />
                Listening...
              </span>
            )}

            {/* Mobile-Only Attach Document Symbol (Goes to Document Upload Ingestion page) */}
            {onOpenDocuments && (
              <button
                type="button"
                onClick={onOpenDocuments}
                className="bui-icon-btn bui-mobile-attach-btn"
                title="Upload & Manage Documents"
                aria-label="Upload documents"
                style={{
                  color: 'var(--bui-ink-3)',
                  transition: 'all 150ms ease'
                }}
              >
                <Paperclip size={15} />
              </button>
            )}

            {/* Voice Input Button */}
            <button
              type="button"
              onClick={toggleVoiceInput}
              className="bui-icon-btn"
              title={isListening ? "Listening... (Click to stop)" : "Voice input (Click to speak)"}
              aria-label="Voice input"
              style={{
                background: isListening ? 'rgba(244, 63, 94, 0.15)' : undefined,
                border: isListening ? '1px solid rgba(244, 63, 94, 0.4)' : undefined,
                color: isListening ? '#f43f5e' : undefined,
                transition: 'all 150ms ease'
              }}
            >
              <Mic size={15} color={isListening ? '#f43f5e' : 'currentColor'} />
            </button>

            {/* Dynamic Send / Stop Button */}
            {isQuerying ? (
              <button
                type="button"
                onClick={onStop}
                className="bui-btn"
                title="Stop generation"
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '10px',
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.4)',
                  color: 'var(--bui-rose)',
                  padding: 0
                }}
              >
                <Square size={14} fill="var(--bui-rose)" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onSend}
                disabled={!queryInput.trim()}
                className="bui-btn bui-btn-primary"
                title="Submit query (Enter)"
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '10px',
                  padding: 0
                }}
              >
                <ArrowUp size={16} strokeWidth={2.6} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
