import { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket.js';
import { useAzureSpeech } from './hooks/useSpeechRecognition.js';
import { SignedIn, SignedOut, UserButton } from '@clerk/clerk-react';
import TranscriptPanel from './components/TranscriptPanel.jsx';
import MemberCard from './components/MemberCard.jsx';
import KnowledgeCard from './components/KnowledgeCard.jsx';
import ComplianceCard from './components/ComplianceCard.jsx';
import SuggestionCard from './components/SuggestionCard.jsx';
import PostCallCard from './components/PostCallCard.jsx';
import FNOLFormCard from './components/FNOLFormCard.jsx';
import LoginPage from './pages/LoginPage.jsx';

// Determine WebSocket URL
// Determine WebSocket URL
// If the page is loaded over HTTPS, use WSS (secure). Otherwise, use WS.
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

const WS_URL = import.meta.env.DEV
    ? `ws://${window.location.hostname}:8000/stream`
    : `${protocol}//${window.location.host}/stream`;

export default function App() {
    const [callActive, setCallActive] = useState(false);
    const [showEvaluation, setShowEvaluation] = useState(false);
    const [postCallTab, setPostCallTab] = useState(0); // 0 = Analytics, 1 = FNOL Form

    const {
        isConnected,
        isProcessing,
        transcripts,
        memberProfile,
        knowledgeDocs,
        complianceAlerts,
        suggestion,
        intent,
        postCallEvaluation,
        sendMessage,
        endCall,
        resetState,
    } = useWebSocket(WS_URL);

    // Azure Speech callback — sends each utterance to the backend
    const onAzureTranscript = useCallback(
        (event) => {
            sendMessage(event.text, event.isFinal, event.speaker, event.offset);
        },
        [sendMessage]
    );

    // Azure Speech hook — token fetched from backend
    const { isListening, error: speechError, toggleListening } = useAzureSpeech({
        onTranscript: onAzureTranscript,
    });

    // ─── Call Lifecycle ─── //
    const handleStartCall = () => {
        resetState();
        setCallActive(true);
        setShowEvaluation(false);
        // Auto-start listening
        setTimeout(() => toggleListening(), 300);
    };

    const handleEndCall = () => {
        if (isListening) toggleListening(); // Stop mic
        endCall(); // Request post-call evaluation
        setCallActive(false);
        setShowEvaluation(true);
    };

    const handleNewCall = () => {
        resetState();
        setCallActive(false);
        setShowEvaluation(false);
        setPostCallTab(0);
    };

    // Connection status
    const statusText = isListening
        ? '🔴 Live — Listening'
        : isProcessing
            ? 'Processing...'
            : isConnected
                ? 'Ready'
                : 'Disconnected';

    const statusClass = isListening
        ? 'processing'
        : isProcessing
            ? 'processing'
            : isConnected
                ? ''
                : 'disconnected';

    return (
        <>
            <SignedOut>
                <LoginPage />
            </SignedOut>
            <SignedIn>
                <div className="app">
                    {/* ─── Header ─── */}
                    <header className="app-header">
                        <div className="header-brand">
                            <img src="/logo.png" alt="Extremum Analytics Logo" className="app-logo" />
                            <h1>
                                <span className="brand-title">Super Call Intelligence</span>
                                <span className="brand-subtitle">Dashboard</span>
                            </h1>
                        </div>
                        <div className="header-status">
                            {intent && (
                                <span className={`intent-badge ${intent.intent}`}>
                                    {intent.intent?.replace(/_/g, ' ')}
                                </span>
                            )}
                            <span className={`status-dot ${statusClass}`} />
                            <span>{statusText}</span>

                            {/* Call controls */}
                            {!callActive && !showEvaluation && (
                                <button className="btn-call start" onClick={handleStartCall} disabled={!isConnected}>
                                    📞 Start Call
                                </button>
                            )}
                            {callActive && (
                                <>
                                    <button
                                        className={`btn-mic-header ${isListening ? 'active' : ''}`}
                                        onClick={toggleListening}
                                        title={isListening ? 'Mute' : 'Unmute'}
                                    >
                                        {isListening ? '🎙️' : '🔇'}
                                    </button>
                                    <button className="btn-call end" onClick={handleEndCall}>
                                        ⏹ End Call
                                    </button>
                                </>
                            )}
                            {showEvaluation && (
                                <button className="btn-call new" onClick={handleNewCall}>
                                    🔄 New Call
                                </button>
                            )}
                            <UserButton />
                        </div>
                    </header>

                    {/* ─── Left: Transcript Panel ─── */}
                    <TranscriptPanel transcripts={transcripts} callActive={callActive} isListening={isListening} />

                    {/* ─── Right: Cards Grid or Post-Call Evaluation ─── */}
                    {showEvaluation && postCallEvaluation ? (
                        <div className="post-call-overlay">
                            <div className="post-call-tabs">
                                <button
                                    className={`post-call-tab${postCallTab === 0 ? ' active' : ''}`}
                                    onClick={() => setPostCallTab(0)}
                                >
                                    📊 Call Analytics
                                </button>
                                <button
                                    className={`post-call-tab${postCallTab === 1 ? ' active' : ''}`}
                                    onClick={() => setPostCallTab(1)}
                                >
                                    📋 FNOL Report
                                </button>
                            </div>
                            <div className="post-call-tab-content">
                                {postCallTab === 0 && <PostCallCard evaluation={postCallEvaluation} />}
                                {postCallTab === 1 && <FNOLFormCard fnolData={postCallEvaluation.fnol_data} />}
                            </div>
                        </div>
                    ) : (
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
                    )}

                    {/* Speech error toast */}
                    {speechError && (
                        <div className="error-toast">
                            ⚠️ Azure Speech: {speechError}
                        </div>
                    )}
                </div>
            </SignedIn>
        </>
    );
}
