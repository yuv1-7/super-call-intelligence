// pages/CallPage.jsx — Active call interface with fixed post-call layout

import { useState, useCallback, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket.js';
import { useDeepgramSpeech } from '../hooks/useSpeechRecognition.js';
import { useAuth } from '@clerk/clerk-react';
import { motion } from 'framer-motion';
import TranscriptPanel from '../components/TranscriptPanel.jsx';
import MemberCard from '../components/MemberCard.jsx';
import KnowledgeCard from '../components/KnowledgeCard.jsx';
import ComplianceCard from '../components/ComplianceCard.jsx';
import SuggestionCard from '../components/SuggestionCard.jsx';
import PostCallCard from '../components/PostCallCard.jsx';
import FNOLFormCard from '../components/FNOLFormCard.jsx';

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = import.meta.env.DEV
    ? `ws://${window.location.hostname}:8000/stream`
    : `${protocol}//${window.location.host}/stream`;

export default function CallPage() {
    const { userId } = useAuth();
    const [callActive, setCallActive] = useState(false);
    const [showEvaluation, setShowEvaluation] = useState(false);
    const [postCallTab, setPostCallTab] = useState(0);

    const {
        isConnected, isProcessing, processingMessage,
        transcripts, memberProfile, knowledgeDocs, complianceAlerts,
        suggestion, intent, postCallEvaluation,
        sendMessage, sendRawMessage, endCall, resetState,
    } = useWebSocket(WS_URL);

    useEffect(() => {
        if (isConnected && userId && sendRawMessage) {
            sendRawMessage({ type: 'auth', clerk_user_id: userId });
        }
    }, [isConnected, userId, sendRawMessage]);

    const onTranscript = useCallback(
        (event) => {
            sendMessage(event.text, event.isFinal, event.speaker, event.offset, event.languages || []);
        },
        [sendMessage]
    );

    const { isListening, error: speechError, toggleListening } = useDeepgramSpeech({ onTranscript });

    const handleStartCall = () => {
        resetState();
        setCallActive(true);
        setShowEvaluation(false);
        setTimeout(() => toggleListening(), 300);
    };

    const handleEndCall = () => {
        if (isListening) toggleListening();
        endCall();
        setCallActive(false);
        setShowEvaluation(true);
    };

    const handleNewCall = () => {
        resetState();
        setCallActive(false);
        setShowEvaluation(false);
        setPostCallTab(0);
    };

    const statusText = isListening
        ? '🔴 Live — Listening'
        : isProcessing
            ? processingMessage || 'Processing...'
            : isConnected
                ? 'Ready'
                : 'Disconnected';

    const statusClass = isListening
        ? 'live'
        : isProcessing
            ? 'processing'
            : isConnected
                ? 'connected'
                : 'disconnected';

    // Post-call evaluation view — full-width, replaces call content
    if (showEvaluation && postCallEvaluation) {
        return (
            <motion.div
                className="call-page"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
            >
                {/* Controls */}
                <div className="call-controls-bar">
                    <div className="call-status-group">
                        <span className="status-badge status-badge--complete">Call Complete</span>
                    </div>
                    <div className="call-buttons-group">
                        <button className="btn-primary" onClick={handleNewCall}>
                            🔄 New Call
                        </button>
                    </div>
                </div>

                {/* Post-Call Content — full width, properly tabbed */}
                <div className="postcall-container">
                    <div className="postcall-tabs">
                        <button
                            className={`postcall-tab ${postCallTab === 0 ? 'active' : ''}`}
                            onClick={() => setPostCallTab(0)}
                        >
                            📊 Call Analytics
                        </button>
                        <button
                            className={`postcall-tab ${postCallTab === 1 ? 'active' : ''}`}
                            onClick={() => setPostCallTab(1)}
                        >
                            📋 FNOL Report
                        </button>
                    </div>
                    <div className="postcall-content">
                        {postCallTab === 0 && <PostCallCard evaluation={postCallEvaluation} />}
                        {postCallTab === 1 && <FNOLFormCard fnolData={postCallEvaluation.fnol_data} />}
                    </div>
                </div>
            </motion.div>
        );
    }

    // Active call / pre-call view
    return (
        <div className="call-page">
            {/* Call Controls Bar */}
            <div className="call-controls-bar">
                <div className="call-status-group">
                    {intent && (
                        <span className={`intent-badge ${intent.intent}`}>
                            {intent.intent?.replace(/_/g, ' ')}
                        </span>
                    )}
                    <span className={`status-dot ${statusClass}`} />
                    <span className="status-text">{statusText}</span>
                </div>
                <div className="call-buttons-group">
                    {!callActive && !showEvaluation && (
                        <button className="btn-call btn-call--start" onClick={handleStartCall} disabled={!isConnected}>
                            📞 Start Call
                        </button>
                    )}
                    {callActive && (
                        <>
                            <button
                                className={`btn-mic ${isListening ? 'active' : ''}`}
                                onClick={toggleListening}
                                title={isListening ? 'Mute' : 'Unmute'}
                            >
                                {isListening ? '🎙️' : '🔇'}
                            </button>
                            <button className="btn-call btn-call--end" onClick={handleEndCall}>
                                ⏹ End Call
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Main Call Content */}
            <div className="call-content">
                <TranscriptPanel transcripts={transcripts} callActive={callActive} isListening={isListening} />

                <main className="cards-area">
                    <SuggestionCard suggestion={suggestion} isProcessing={isProcessing} />
                    <div className="cards-scroll">
                        <div className="cards-row">
                            <KnowledgeCard docs={knowledgeDocs} />
                            <MemberCard member={memberProfile} />
                        </div>
                        <ComplianceCard alerts={complianceAlerts} />
                    </div>
                </main>
            </div>

            {speechError && (
                <div className="error-toast">
                    ⚠️ Speech Error: {speechError}
                </div>
            )}
        </div>
    );
}
