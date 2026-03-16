/**
 * Post-Call Evaluation Scorecard — Rubric-Based Agent Performance Analysis
 * Shows after "End Call" with 7-section rubric scoring, caller insights,
 * skill observations, compliance flags, and improvement notes.
 */
export default function PostCallCard({ evaluation }) {
    if (!evaluation) return null;

    const {
        overall_score,
        grade,
        call_type,
        call_outcome,
        call_summary,
        call_events = [],
        caller_insights,
        skill_observations = [],
        procedure_gaps = [],
        strong_moments = [],
        compliance_flags = [],
        compliance_summary,
        missed_opportunities = [],
        recurring_risk_indicators = [],
        positive_indicators = [],
        agent_improvement_notes = [],
        sections = [],
        auto_fails = [],
        fnol_completeness_pct,
        fnol_points_earned,
        fnol_points_possible,
        fnol_fields_collected = [],
        fnol_fields_missing = [],
        call_duration_seconds,
        total_utterances,
        agent_utterances,
        customer_utterances,
    } = evaluation;

    const getOverallColor = (score) => {
        if (score >= 75) return 'var(--accent-green)';
        if (score >= 60) return 'var(--accent-amber)';
        if (score >= 45) return '#f97316';
        return 'var(--accent-red)';
    };

    const getSectionColor = (awarded, possible) => {
        if (possible === 0) return 'var(--text-secondary)';
        const pct = awarded / possible;
        if (pct >= 0.8) return 'var(--accent-green)';
        if (pct >= 0.6) return 'var(--accent-amber)';
        return 'var(--accent-red)';
    };

    const formatDuration = (secs) => {
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        return `${m}m ${s}s`;
    };

    return (
        <div className="post-call-card">
            {/* ─── Header ─── */}
            <div className="post-call-header">
                <div className="post-call-title">
                    <span className="post-call-icon">📊</span>
                    <div>
                        <h2>Post-Call Evaluation</h2>
                        <p className="post-call-subtitle">{grade} — {call_type || 'Insurance Call'}</p>
                    </div>
                </div>
                <div className="overall-score-circle" style={{ borderColor: getOverallColor(overall_score) }}>
                    <span className="score-number" style={{ color: getOverallColor(overall_score) }}>
                        {overall_score}
                    </span>
                    <span className="score-label">/ 100</span>
                </div>
            </div>

            {/* ─── Call Summary ─── */}
            <div className="post-call-summary">
                <p>{call_summary}</p>
                {call_outcome && (
                    <p className="call-outcome"><strong>Outcome:</strong> {call_outcome}</p>
                )}
            </div>

            {/* ─── Call Metrics ─── */}
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
                <div className="metric">
                    <span className="metric-value" style={{ color: getOverallColor(fnol_completeness_pct || 0) }}>
                        {fnol_completeness_pct || 0}%
                    </span>
                    <span className="metric-label">FNOL Complete</span>
                </div>
            </div>

            {/* ─── Auto-Fail Alerts ─── */}
            {auto_fails.length > 0 && (
                <div className="auto-fail-banner">
                    <h4>🚨 Auto-Fail Triggered</h4>
                    <ul>
                        {auto_fails.map((af, i) => <li key={i}>{af}</li>)}
                    </ul>
                </div>
            )}

            {/* ─── Rubric Sections (7 sections) ─── */}
            <div className="score-categories">
                {sections.map((section, idx) => {
                    const pct = section.points_possible > 0
                        ? (section.points_awarded / section.points_possible) * 100
                        : 0;
                    const color = getSectionColor(section.points_awarded, section.points_possible);

                    return (
                        <div key={idx} className={`score-category${section.auto_failed ? ' auto-failed' : ''}`}>
                            <div className="score-category-header">
                                <span>
                                    {section.auto_failed && '🚫 '}
                                    {section.section_name}
                                </span>
                                <span className="category-score" style={{ color }}>
                                    {section.points_awarded}/{section.points_possible}
                                </span>
                            </div>
                            <div className="score-bar">
                                <div
                                    className="score-bar-fill"
                                    style={{ width: `${pct}%`, background: color }}
                                />
                            </div>
                            {section.auto_failed && section.auto_fail_reason && (
                                <p className="auto-fail-reason">⚠️ {section.auto_fail_reason}</p>
                            )}
                            {/* Rubric items */}
                            <div className="rubric-items">
                                {(section.rubric_items || []).map((item, ri) => (
                                    <div key={ri} className={`rubric-item ${item.passed ? 'passed' : 'failed'}`}>
                                        <div className="rubric-item-header">
                                            <span>{item.passed ? '✅' : '❌'} {item.criterion}</span>
                                            <span className="rubric-points">
                                                {item.points_awarded}/{item.points_possible}
                                            </span>
                                        </div>
                                        <p className="rubric-evidence">{item.evidence}</p>
                                        {item.deduction_reason && (
                                            <p className="rubric-deduction">📝 {item.deduction_reason}</p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* ─── Caller Insights ─── */}
            {caller_insights && (
                <div className="feedback-section caller-insights">
                    <h4>🧑 Caller Profile</h4>
                    <div className="caller-grid">
                        <div className="caller-field">
                            <span className="label">Description</span>
                            <span className="value">{caller_insights.caller_description}</span>
                        </div>
                        <div className="caller-field">
                            <span className="label">Emotional State</span>
                            <span className="value">{caller_insights.emotional_state}</span>
                        </div>
                        <div className="caller-field">
                            <span className="label">Communication</span>
                            <span className="value">{caller_insights.communication_style}</span>
                        </div>
                        <div className="caller-field">
                            <span className="label">Cooperation</span>
                            <span className="value">{caller_insights.cooperation_level}</span>
                        </div>
                        <div className="caller-field">
                            <span className="label">Difficulty</span>
                            <span className="value">{caller_insights.difficulty_score}/5 — {caller_insights.difficulty_rationale}</span>
                        </div>
                    </div>
                    {caller_insights.notable_behaviors?.length > 0 && (
                        <div style={{ marginTop: '8px' }}>
                            <span className="label">Notable Behaviors</span>
                            <ul>
                                {caller_insights.notable_behaviors.map((b, i) => <li key={i}>{b}</li>)}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {/* ─── Skill Observations ─── */}
            {skill_observations.length > 0 && (
                <div className="feedback-section">
                    <h4>🔍 Skill Observations</h4>
                    <div className="skill-observations-list">
                        {skill_observations.map((obs, i) => (
                            <div key={i} className={`skill-obs ${obs.valence}`}>
                                <div className="skill-obs-header">
                                    <span>{obs.valence === 'positive' ? '👍' : obs.valence === 'negative' ? '👎' : '➡️'} {obs.skill_area}</span>
                                </div>
                                <p>{obs.observation}</p>
                                <p className="skill-impact"><em>Impact: {obs.impact}</em></p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ─── Strengths & Improvements ─── */}
            <div className="feedback-grid">
                {strong_moments.length > 0 && (
                    <div className="feedback-section strengths">
                        <h4>💪 Strong Moments</h4>
                        <ul>
                            {strong_moments.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                    </div>
                )}
                {agent_improvement_notes.length > 0 && (
                    <div className="feedback-section improvements">
                        <h4>📈 Improvement Notes</h4>
                        <ul>
                            {agent_improvement_notes.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                    </div>
                )}
            </div>

            {/* ─── Compliance Flags ─── */}
            {compliance_flags.length > 0 && (
                <div className="compliance-section">
                    <h4>⚠️ Compliance Flags</h4>
                    {compliance_flags.map((flag, i) => (
                        <div key={i} className={`compliance-flag severity-${flag.severity}`}>
                            <div className="flag-header">
                                <span className="flag-type">{flag.flag_type}</span>
                                <span className={`flag-severity ${flag.severity}`}>{flag.severity}</span>
                            </div>
                            <p>{flag.description}</p>
                            {flag.agent_quote && <p className="flag-quote">"{flag.agent_quote}"</p>}
                            <p className="flag-risk"><strong>Risk:</strong> {flag.risk}</p>
                        </div>
                    ))}
                    {compliance_summary && <p className="compliance-summary-text">{compliance_summary}</p>}
                </div>
            )}

            {/* ─── Missed Opportunities ─── */}
            {missed_opportunities.length > 0 && (
                <div className="feedback-section">
                    <h4>🎯 Missed Opportunities</h4>
                    {missed_opportunities.map((mo, i) => (
                        <div key={i} className="missed-opp">
                            <p><strong>Moment:</strong> {mo.moment}</p>
                            <p><strong>What happened:</strong> {mo.what_happened}</p>
                            <p><strong>Better approach:</strong> {mo.better_approach}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* ─── FNOL Completeness ─── */}
            {(fnol_fields_collected.length > 0 || fnol_fields_missing.length > 0) && (
                <div className="feedback-section">
                    <h4>📋 FNOL Data Collected ({fnol_points_earned}/{fnol_points_possible} pts)</h4>
                    <div className="fnol-completeness-grid">
                        {fnol_fields_collected.map((f, i) => (
                            <span key={`c${i}`} className="fnol-chip collected">✅ {f.field}</span>
                        ))}
                        {fnol_fields_missing.map((f, i) => (
                            <span key={`m${i}`} className="fnol-chip missing">❌ {f.field}</span>
                        ))}
                    </div>
                </div>
            )}

            {/* ─── Risk & Positive Indicators ─── */}
            <div className="feedback-grid">
                {positive_indicators.length > 0 && (
                    <div className="feedback-section strengths">
                        <h4>✅ Positive Indicators</h4>
                        <ul>
                            {positive_indicators.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                    </div>
                )}
                {recurring_risk_indicators.length > 0 && (
                    <div className="feedback-section improvements">
                        <h4>🔴 Risk Indicators</h4>
                        <ul>
                            {recurring_risk_indicators.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}
