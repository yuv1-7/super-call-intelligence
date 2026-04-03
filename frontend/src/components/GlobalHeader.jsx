import { useNavigate } from 'react-router-dom';
import { UserButton } from '@clerk/clerk-react';
import { useCall } from '../context/CallContext.jsx';

export default function GlobalHeader({ userRole }) {
    const navigate = useNavigate();
    const {
        isConnected, isProcessing, processingMessage, isListening,
        callActive, showEvaluation, intent, callElapsed,
        handleStartCall, handleEndCall, handleNewCall, toggleListening,
        aiEnabled, aiSpeaking, handleToggleAi
    } = useCall();

    const timerStr = callActive
        ? `${String(Math.floor(callElapsed / 60)).padStart(2, '0')}:${String(callElapsed % 60).padStart(2, '0')}`
        : null;

    const statusText = isListening ? '🔴 Live — Listening' : isProcessing ? processingMessage || 'Processing...' : isConnected ? 'Ready' : 'Disconnected';
    const statusClass = isListening ? 'live' : isProcessing ? 'processing' : isConnected ? 'connected' : 'disconnected';

    const roleLabel = (userRole || 'agent').replace('_', ' ');
    const roleIcon = userRole === 'manager' ? '👔' : userRole === 'team_lead' ? '👥' : '🎧';

    return (
        <header className="global-header">
            {/* Left Box: Logo + Status */}
            <div className="global-header-left">
                <div className="global-header-brand" onClick={() => navigate('/')}>
                    <img src="/logo.png" alt="CallIQ" className="global-header-logo" />
                    <div className="global-header-text">
                        <span className="global-header-title">CallIQ</span>
                        <span className="global-header-subtitle">Intelligence</span>
                    </div>
                </div>

                <div className="global-header-divider" />

                <div className="global-header-status">
                    {showEvaluation ? (
                        <div className="call-status-group">
                            <span className="status-badge status-badge--complete">Call Complete</span>
                        </div>
                    ) : (
                        <div className="call-status-group">
                            {intent && (
                                <span className={`intent-badge ${intent.intent}`}>
                                    {intent.intent?.replace(/_/g, ' ')}
                                </span>
                            )}
                            <span className={`status-dot ${statusClass}`} />
                            <span className="status-text">{statusText}</span>
                            {timerStr && (
                                <span className="call-timer" title="Call duration">{timerStr}</span>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Right Box: Actions + Profile */}
            <div className="global-header-right">
                <div className="global-header-actions">
                    {showEvaluation ? (
                        <div className="call-buttons-group">
                            <button className="btn-primary" onClick={handleNewCall}>
                                🔄 New Call
                            </button>
                        </div>
                    ) : (
                        <div className="call-buttons-group">
                            {!callActive && (
                                <>
                                    <button
                                        className={`btn-ai-toggle ${aiEnabled ? 'active' : ''}`}
                                        onClick={handleToggleAi}
                                        title={aiEnabled ? 'Disable AI Auto-Speak' : 'Enable AI Auto-Speak'}
                                        id="ai-toggle-btn"
                                    >
                                        <span className="btn-ai-icon">{aiEnabled ? '🤖' : '🤖'}</span>
                                        <span className="btn-ai-label">{aiEnabled ? 'AI On' : 'AI Off'}</span>
                                        {aiSpeaking && <span className="ai-speaking-wave" />}
                                    </button>
                                    <button className="btn-call btn-call--start" onClick={handleStartCall}>
                                        📞 Start Call
                                    </button>
                                </>
                            )}
                            {callActive && (
                                <>
                                    <button
                                        className={`btn-ai-toggle ${aiEnabled ? 'active' : ''} ${aiSpeaking ? 'speaking' : ''}`}
                                        onClick={handleToggleAi}
                                        title={aiEnabled ? 'Disable AI Auto-Speak' : 'Enable AI Auto-Speak'}
                                        id="ai-toggle-btn"
                                    >
                                        <span className="btn-ai-icon">{aiEnabled ? '🤖' : '🤖'}</span>
                                        <span className="btn-ai-label">{aiEnabled ? 'AI On' : 'AI Off'}</span>
                                        {aiSpeaking && <span className="ai-speaking-wave" />}
                                    </button>
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
                    )}
                </div>

                <div className="global-header-divider" />

                <div className="header-role-badge" title={roleLabel}>
                    <span className="header-role-icon">{roleIcon}</span>
                    <span className="header-role-text">{roleLabel}</span>
                </div>

                <UserButton />
            </div>
        </header>
    );
}
