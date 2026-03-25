import { useRef, useEffect } from 'react';
import { Mic, Activity, Headphones, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Live transcript panel with speaker diarization.
 */
export default function TranscriptPanel({ transcripts, callActive, isListening }) {
    const bottomRef = useRef(null);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (bottomRef.current) {
                const parent = bottomRef.current.parentElement;
                // scroll the specific container, avoids scrolling the entire app layout
                parent.scrollTop = parent.scrollHeight;
            }
        }, 100);
        return () => clearTimeout(timer);
    }, [transcripts]);

    const getSpeakerClass = (speaker) => {
        if (!speaker) return '';
        const s = speaker.toLowerCase();
        if (s.includes('agent')) return 'speaker-agent';
        if (s.includes('customer')) return 'speaker-customer';
        return 'speaker-unknown';
    };

    return (
        <div className="transcript-panel">
            <div className="panel-header">
                <div className="panel-header-title">
                    <Activity size={18} className="icon-pulse" />
                    <span>Live Transcript Stream</span>
                </div>
                {isListening && (
                    <div className="live-status-badge">
                        <span className="live-dot pulse" />
                        <span>LIVE</span>
                    </div>
                )}
            </div>
            
            <div className="transcript-messages">
                <AnimatePresence>
                    {transcripts.length === 0 && (
                        <motion.div 
                            className="transcript-empty"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                        >
                            <div className="empty-illustration">
                                <Headphones size={48} strokeWidth={1.5} />
                                <div className="illustration-glow" />
                            </div>
                            <h3>{callActive ? 'Listening for audio...' : 'No Active Call'}</h3>
                            <p>
                                {callActive
                                    ? 'Start speaking to see real-time transcription and AI analysis.'
                                    : 'Click "Start Call" to begin the live intelligence stream.'}
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>

                {transcripts.map((t, idx) => (
                    <motion.div
                        key={t.id || idx}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className={`transcript-line ${t.is_finalized ? 'finalized' : 'partial'} ${getSpeakerClass(t.speaker)}`}
                    >
                        {t.speaker && t.is_finalized && (
                            <div className="transcript-meta">
                                <span className={`speaker-name ${getSpeakerClass(t.speaker)}`}>
                                    {t.speaker}
                                </span>
                                <span className="transcript-time">{t.timestamp}</span>
                            </div>
                        )}
                        <div className="transcript-bubble">
                            <p className="transcript-text">
                                {t.text}
                            </p>
                            {!t.is_finalized && <span className="typing-indicator">...</span>}
                        </div>
                    </motion.div>
                ))}
                <div ref={bottomRef} style={{ height: '20px' }} />
            </div>
        </div>
    );
}
