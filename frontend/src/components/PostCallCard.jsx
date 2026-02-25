/**
 * Post-Call Evaluation Scorecard — Agent Performance Analysis
 * Shows after "End Call" with detailed scoring across 5 categories.
 */
export default function PostCallCard({ evaluation }) {
    if (!evaluation) return null;

    const {
        overall_score,
        call_summary,
        scores = {},
        strengths = [],
        improvements = [],
        compliance_violations = [],
        coaching_notes,
        call_duration_seconds,
        total_utterances,
        agent_utterances,
        customer_utterances,
    } = evaluation;

    const getScoreColor = (score) => {
        if (score >= 8) return 'var(--accent-green)';
        if (score >= 5) return 'var(--accent-amber)';
        return 'var(--accent-red)';
    };

    const getOverallColor = (score) => {
        if (score >= 80) return 'var(--accent-green)';
        if (score >= 50) return 'var(--accent-amber)';
        return 'var(--accent-red)';
    };

    const formatDuration = (secs) => {
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        return `${m}m ${s}s`;
    };

    const categories = [
        { key: 'empathy_and_tone', label: 'Empathy & Tone', icon: '💛' },
        { key: 'information_gathering', label: 'Information Gathering', icon: '📋' },
        { key: 'compliance_adherence', label: 'Compliance', icon: '⚖️' },
        { key: 'process_knowledge', label: 'Process Knowledge', icon: '📖' },
        { key: 'resolution_and_next_steps', label: 'Resolution & Next Steps', icon: '✅' },
    ];

    return (
        <div className="post-call-card">
            {/* Header */}
            <div className="post-call-header">
                <div className="post-call-title">
                    <span className="post-call-icon">📊</span>
                    <div>
                        <h2>Post-Call Evaluation</h2>
                        <p className="post-call-subtitle">Agent Performance Scorecard</p>
                    </div>
                </div>
                <div className="overall-score-circle" style={{ borderColor: getOverallColor(overall_score) }}>
                    <span className="score-number" style={{ color: getOverallColor(overall_score) }}>
                        {overall_score}
                    </span>
                    <span className="score-label">/ 100</span>
                </div>
            </div>

            {/* Call Summary */}
            <div className="post-call-summary">
                <p>{call_summary}</p>
            </div>

            {/* Call Metrics */}
            <div className="call-metrics">
                <div className="metric">
                    <span className="metric-value">{formatDuration(call_duration_seconds || 0)}</span>
                    <span className="metric-label">Duration</span>
                </div>
                <div className="metric">
                    <span className="metric-value">{total_utterances || 0}</span>
                    <span className="metric-label">Utterances</span>
                </div>
                <div className="metric">
                    <span className="metric-value">{agent_utterances || 0}</span>
                    <span className="metric-label">Agent</span>
                </div>
                <div className="metric">
                    <span className="metric-value">{customer_utterances || 0}</span>
                    <span className="metric-label">Customer</span>
                </div>
            </div>

            {/* Category Scores */}
            <div className="score-categories">
                {categories.map(({ key, label, icon }) => {
                    const cat = scores[key];
                    if (!cat) return null;
                    return (
                        <div key={key} className="score-category">
                            <div className="score-category-header">
                                <span>{icon} {label}</span>
                                <span
                                    className="category-score"
                                    style={{ color: getScoreColor(cat.score) }}
                                >
                                    {cat.score}/10
                                </span>
                            </div>
                            <div className="score-bar">
                                <div
                                    className="score-bar-fill"
                                    style={{
                                        width: `${cat.score * 10}%`,
                                        background: getScoreColor(cat.score),
                                    }}
                                />
                            </div>
                            <p className="score-feedback">{cat.feedback}</p>
                        </div>
                    );
                })}
            </div>

            {/* Strengths & Improvements */}
            <div className="feedback-grid">
                <div className="feedback-section strengths">
                    <h4>💪 Strengths</h4>
                    <ul>
                        {strengths.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
                <div className="feedback-section improvements">
                    <h4>📈 Areas for Improvement</h4>
                    <ul>
                        {improvements.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* Compliance Violations */}
            {compliance_violations.length > 0 && (
                <div className="compliance-section">
                    <h4>⚠️ Compliance Notes</h4>
                    <ul>
                        {compliance_violations.map((v, i) => (
                            <li key={i}>{v}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Coaching Notes */}
            {coaching_notes && (
                <div className="coaching-section">
                    <h4>🎯 Coaching Notes</h4>
                    <p>{coaching_notes}</p>
                </div>
            )}
        </div>
    );
}
