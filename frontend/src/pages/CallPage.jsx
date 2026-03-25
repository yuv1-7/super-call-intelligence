import { motion } from 'framer-motion';
import { useCall } from '../context/CallContext.jsx';
import TranscriptPanel from '../components/TranscriptPanel.jsx';
import MemberCard from '../components/MemberCard.jsx';
import KnowledgeCard from '../components/KnowledgeCard.jsx';
import ComplianceCard from '../components/ComplianceCard.jsx';
import SuggestionCard from '../components/SuggestionCard.jsx';
import PostCallCard from '../components/PostCallCard.jsx';
import FNOLFormCard from '../components/FNOLFormCard.jsx';

export default function CallPage() {
    const {
        callActive, showEvaluation, postCallTab, setPostCallTab,
        transcripts, memberProfile, memberLookupStatus, knowledgeDocs, complianceAlerts,
        suggestion, postCallEvaluation, error: speechError, isListening
    } = useCall();

    // Post-call evaluation view — full-width, replaces call content
    if (showEvaluation && postCallEvaluation) {
        return (
            <motion.div
                className="call-page"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
            >
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

    // Active call view
    return (
        <div className="call-page">
            {/* Main Call Content */}
            <div className="call-content">
                <TranscriptPanel transcripts={transcripts} callActive={callActive} isListening={isListening} />

                {showEvaluation && !postCallEvaluation ? (
                    <motion.main 
                        className="cards-area"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.3 }}
                    >
                        <div style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%',
                            background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)'
                        }}>
                            <div className="spinner" style={{ 
                                width: 48, height: 48, border: '4px solid var(--border-subtle)', borderTopColor: 'var(--accent-blue)', 
                                borderRadius: '50%', animation: 'spin 1.2s cubic-bezier(0.55, 0.15, 0.45, 0.85) infinite', marginBottom: 24, boxShadow: '0 0 16px rgba(99, 102, 241, 0.3)'
                            }} />
                            <h3 style={{ margin: '0 0 8px', color: 'var(--text-primary)', fontSize: '1.25rem'}}>
                                Generating Post-Call Summary
                                <motion.span
                                    animate={{ opacity: [0, 1, 0] }}
                                    transition={{ repeat: Infinity, duration: 1.5 }}
                                >
                                    ...
                                </motion.span>
                            </h3>
                            <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.95rem' }}>
                                Analyzing transcript and calculating conversational metrics
                            </p>
                        </div>
                    </motion.main>
                ) : (
                    <main className="cards-area">
                        <SuggestionCard suggestion={suggestion} />
                        <div className="cards-scroll">
                            <div className="cards-row">
                                <KnowledgeCard docs={knowledgeDocs} />
                                <MemberCard member={memberProfile} lookupStatus={memberLookupStatus} />
                            </div>
                            <ComplianceCard alerts={complianceAlerts} />
                        </div>
                    </main>
                )}
            </div>

            {speechError && (
                <div className="error-toast">
                    ⚠️ Speech Error: {speechError}
                </div>
            )}
        </div>
    );
}
