import { useState, useEffect, useRef } from 'react';

export default function SuggestionCard({ suggestion, isProcessing, isSuggestionDone }) {
    const [aiVoiceEnabled, setAiVoiceEnabled] = useState(false);
    const audioRef = useRef(null);

    // Watch for completed suggestions to auto-play if enabled
    useEffect(() => {
        if (isSuggestionDone && aiVoiceEnabled && suggestion) {
            const playAudio = async () => {
                try {
                    const response = await fetch('/api/tts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: suggestion })
                    });
                    
                    if (response.ok) {
                        const audioBlob = await response.blob();
                        const audioUrl = URL.createObjectURL(audioBlob);
                        
                        if (audioRef.current) {
                            audioRef.current.pause();
                        }
                        
                        const audio = new Audio(audioUrl);
                        audioRef.current = audio;
                        audio.play();
                    } else {
                        console.error('TTS request failed', await response.text());
                    }
                } catch (e) {
                    console.error('Error playing TTS audio', e);
                }
            };
            playAudio();
        }
    }, [isSuggestionDone, suggestion, aiVoiceEnabled]);

    const voiceToggle = (
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer', userSelect: 'none' }}>
            <span>Enable AI Voice</span>
            <input 
                type="checkbox" 
                checked={aiVoiceEnabled} 
                onChange={(e) => setAiVoiceEnabled(e.target.checked)} 
                style={{ cursor: 'pointer' }}
            />
        </label>
    );

    if (isProcessing && !suggestion) {
        return (
            <div className="card suggestion">
                <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <div className="card-icon">💡</div>
                        <div>
                            <div className="card-title">Suggested Response</div>
                            <div className="card-subtitle">Generating...</div>
                        </div>
                    </div>
                    {voiceToggle}
                </div>
                <div className="card-body">
                    <div className="suggestion-shimmer">
                        <div className="shimmer-line" />
                        <div className="shimmer-line" />
                        <div className="shimmer-line" />
                    </div>
                </div>
            </div>
        );
    }

    if (!suggestion) {
        return (
            <div className="card suggestion empty">
                <div className="empty-state">
                    <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%', marginBottom: '16px' }}>
                        {voiceToggle}
                    </div>
                    <div className="empty-icon">💡</div>
                    <h3>Suggested Response</h3>
                    <p>AI-generated talking points for the agent will appear here</p>
                </div>
            </div>
        );
    }

    // Render as a single flowing block with visual paragraph breaks.
    // Previous implementation split on \n\n into separate highlighted bubbles
    // which made long scripts hard to read aloud.
    const paragraphs = suggestion
        .split('\n\n')
        .map(s => s.trim())
        .filter(s => s.length > 0);

    const isUpdating = isProcessing && suggestion;

    return (
        <div className={`card suggestion${isUpdating ? ' updating' : ''}`}>
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <div className="card-icon">💡</div>
                    <div>
                        <div className="card-title">Suggested Response</div>
                        <div className="card-subtitle">
                            {isUpdating ? 'Updating...' : 'Ready to use'}
                        </div>
                    </div>
                </div>
                {voiceToggle}
            </div>
            <div className="card-body">
                <div className="suggestion-text">
                    <span className="highlight-script">
                        {paragraphs.map((text, idx) => (
                            <span key={idx}>
                                {idx > 0 && <><br /><br /></>}
                                {text}
                            </span>
                        ))}
                    </span>
                    {isProcessing && (
                        <div className="suggestion-shimmer" style={{ marginTop: '4px' }}>
                            <div className="shimmer-line" />
                            <div className="shimmer-line" />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
