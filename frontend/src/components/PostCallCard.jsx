/**
 * Post-Call Evaluation Scorecard — Rubric-Based Agent Performance Analysis
 * Displays detailed rubric scoring with evidence, auto-fail banners,
 * grade badges, FNOL completeness, and coaching notes.
 */
import { useState } from 'react';

export default function PostCallCard({ evaluation }) {
    if (!evaluation) return null;

    const {
        overall_score,
        grade,
        call_summary,
        caller_profile,
        call_highlights = [],
        sections = [],
        auto_fails = [],
        strengths = [],
        improvements = [],
        coaching_notes,
        recommended_supervisor_action,
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

    const [expandedSections, setExpandedSections] = useState({});

    const toggleSection = (idx) => {
        setExpandedSections((prev) => ({ ...prev, [idx]: !prev[idx] }));
    };

    const getGradeColor = (g) => {
        switch (g) {
            case 'Exceptional': return 'var(--accent-green)';
            case 'Proficient': return '#60a5fa';
            case 'Developing': return 'var(--accent-amber)';
            case 'Needs Improvement': return '#f97316';
            case 'Critical Issues': return 'var(--accent-red)';
            default: return 'var(--text-muted)';
        }
    };

    const getScoreColor = (pct) => {
        if (pct >= 80) return 'var(--accent-green)';
        if (pct >= 50) return 'var(--accent-amber)';
        return 'var(--accent-red)';
    };

    const formatDuration = (secs) => {
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        return `${m}m ${s}s`;
    };

    const gradeColor = getGradeColor(grade);

    return (
        <div className="post-call-card">
            {/* ─── Auto-Fail Banner ─── */}
            {auto_fails.length > 0 && (
                <div className="auto-fail-banner">
                    <div className="auto-fail-icon">🚨</div>
                    <div className="auto-fail-content">
                        <strong>Auto-Fail Triggered</strong>
                        {auto_fails.map((fail, i) => (
                            <p key={i}>{fail}</p>
                        ))}
                    </div>
                </div>
            )}

            {/* ─── Supervisor Escalation ─── */}
            {recommended_supervisor_action && (
                <div className="supervisor-banner">
                    <div className="supervisor-icon">⚠️</div>
                    <div className="supervisor-content">
                        <strong>Supervisor Action Required</strong>
                        <p>{recommended_supervisor_action}</p>
                    </div>
                </div>
            )}

            {/* ─── Header with Score + Grade ─── */}
            <div className="post-call-header">
                <div className="post-call-title">
                    <span className="post-call-icon">📊</span>
                    <div>
                        <h2>Post-Call Evaluation</h2>
                        <p className="post-call-subtitle">Rubric-Based Performance Scorecard</p>
                    </div>
                </div>
                <div className="score-grade-group">
                    <div className="overall-score-circle" style={{ borderColor: gradeColor }}>
                        <span className="score-number" style={{ color: gradeColor }}>
                            {overall_score}
                        </span>
                        <span className="score-label">/ 100</span>
                    </div>
                    <span className="grade-badge" style={{ background: gradeColor }}>
                        {grade}
                    </span>
                </div>
            </div>

            {/* ─── Call Report ─── */}
            <div className="call-report-section">
                <div className="call-report-narrative">
                    <h4>📝 Call Summary</h4>
                    {call_summary && call_summary.split('\n').filter(p => p.trim()).map((para, i) => (
                        <p key={i}>{para}</p>
                    ))}
                </div>

                {caller_profile && (
                    <div className="caller-profile-box">
                        <h4>🗣️ Caller Profile</h4>
                        <p>{caller_profile}</p>
                    </div>
                )}

                {call_highlights.length > 0 && (
                    <div className="call-highlights">
                        <h4>📌 Key Moments</h4>
                        <ul>
                            {call_highlights.map((h, i) => (
                                <li key={i}>{h}</li>
                            ))}
                        </ul>
                    </div>
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
            </div>

            {/* ─── Rubric Sections ─── */}
            <div className="rubric-sections">
                {sections.map((section, idx) => {
                    const pct = section.points_possible > 0
                        ? Math.round((section.points_awarded / section.points_possible) * 100)
                        : 0;
                    const isExpanded = expandedSections[idx];
                    const sectionColor = section.auto_failed
                        ? 'var(--accent-red)'
                        : getScoreColor(pct);

                    return (
                        <div key={idx} className={`rubric-section ${section.auto_failed ? 'auto-failed' : ''}`}>
                            <button
                                className="rubric-section-header"
                                onClick={() => toggleSection(idx)}
                            >
                                <div className="rubric-section-left">
                                    <span className="rubric-expand-icon">
                                        {isExpanded ? '▾' : '▸'}
                                    </span>
                                    <span className="rubric-section-name">
                                        {section.section_name}
                                    </span>
                                    {section.auto_failed && (
                                        <span className="auto-fail-tag">AUTO-FAIL</span>
                                    )}
                                </div>
                                <div className="rubric-section-right">
                                    <span className="rubric-section-score" style={{ color: sectionColor }}>
                                        {section.points_awarded}/{section.points_possible}
                                    </span>
                                    <div className="rubric-section-bar">
                                        <div
                                            className="rubric-section-bar-fill"
                                            style={{
                                                width: `${pct}%`,
                                                background: sectionColor,
                                            }}
                                        />
                                    </div>
                                </div>
                            </button>

                            {isExpanded && (
                                <div className="rubric-items">
                                    {section.auto_failed && section.auto_fail_reason && (
                                        <div className="auto-fail-reason">
                                            🚨 {section.auto_fail_reason}
                                        </div>
                                    )}
                                    {section.rubric_items.map((item, itemIdx) => (
                                        <div key={itemIdx} className={`rubric-item ${item.passed ? 'passed' : 'failed'}`}>
                                            <div className="rubric-item-header">
                                                <span className="rubric-item-status">
                                                    {item.passed ? '✅' : '❌'}
                                                </span>
                                                <span className="rubric-item-criterion">
                                                    {item.criterion}
                                                </span>
                                                <span className="rubric-item-points" style={{
                                                    color: item.passed ? 'var(--accent-green)' : 'var(--accent-red)'
                                                }}>
                                                    {item.points_awarded}/{item.points_possible}
                                                </span>
                                            </div>
                                            {item.evidence && item.evidence !== 'Not found' && (
                                                <div className="rubric-item-evidence">
                                                    <span className="evidence-label">Evidence:</span>
                                                    "{item.evidence}"
                                                </div>
                                            )}
                                            {item.deduction_reason && (
                                                <div className="rubric-item-deduction">
                                                    ⚠️ {item.deduction_reason}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* ─── FNOL Completeness ─── */}
            <div className="fnol-completeness-section">
                <div className="fnol-completeness-header">
                    <h4>📋 FNOL Data Completeness</h4>
                    <span className="fnol-completeness-score" style={{
                        color: getScoreColor(fnol_completeness_pct || 0)
                    }}>
                        {fnol_completeness_pct || 0}%
                        <span className="fnol-points-detail">
                            ({fnol_points_earned || 0}/{fnol_points_possible || 0} pts)
                        </span>
                    </span>
                </div>
                <div className="fnol-completeness-bar">
                    <div
                        className="fnol-completeness-bar-fill"
                        style={{
                            width: `${fnol_completeness_pct || 0}%`,
                            background: getScoreColor(fnol_completeness_pct || 0),
                        }}
                    />
                </div>
                <div className="fnol-fields-grid">
                    {fnol_fields_collected.map((f, i) => (
                        <div key={`c-${i}`} className="fnol-field-item collected">
                            <span className="fnol-field-status">✅</span>
                            <div className="fnol-field-info">
                                <span className="fnol-field-name">{f.field}</span>
                                <span className="fnol-field-value">{f.value}</span>
                            </div>
                            <span className="fnol-field-pts">{f.points}pts</span>
                        </div>
                    ))}
                    {fnol_fields_missing.map((f, i) => (
                        <div key={`m-${i}`} className="fnol-field-item missing">
                            <span className="fnol-field-status">❌</span>
                            <div className="fnol-field-info">
                                <span className="fnol-field-name">{f.field}</span>
                                <span className="fnol-field-value not-collected">Not collected</span>
                            </div>
                            <span className="fnol-field-pts">0/{f.points}pts</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* ─── Strengths & Improvements ─── */}
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

            {/* ─── Coaching Notes ─── */}
            {coaching_notes && (
                <div className="coaching-section">
                    <h4>🎯 Coaching Notes</h4>
                    <p>{coaching_notes}</p>
                </div>
            )}
        </div>
    );
}
