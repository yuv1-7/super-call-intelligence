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
            </div>

            {speechError && (
                <div className="error-toast">
                    ⚠️ Speech Error: {speechError}
                </div>
            )}
        </div>
    );
}
