/**
 * PostCallCard v3 — Insight-rich evaluation for supervisor review + agent self-improvement
 *
 * Tab 1 — Call Summary:   What happened, who called, how the call went
 * Tab 2 — Agent Insights: Skill observations, procedure gaps, patterns
 * Tab 3 — QA Scorecard:   Per-criterion rubric with evidence
 * Tab 4 — Compliance & Improvement: Flags, missed opportunities, agent notes
 */
import { useState } from 'react';

// ─── Config ──────────────────────────────────────────────────────────────────

const TABS = [
    { id: 'summary', icon: '📋', label: 'Call Summary' },
    { id: 'insights', icon: '🔍', label: 'Agent Insights' },
    { id: 'scorecard', icon: '📊', label: 'QA Scorecard' },
    { id: 'improvement', icon: '📈', label: 'Improvement' },
];

const GRADE_STYLE = {
    'Exceptional': { color: '#34d399', bg: 'rgba(52,211,153,0.1)', ring: 'rgba(52,211,153,0.3)' },
    'Proficient': { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', ring: 'rgba(96,165,250,0.3)' },
    'Developing': { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', ring: 'rgba(251,191,36,0.3)' },
    'Needs Improvement': { color: '#f97316', bg: 'rgba(249,115,22,0.1)', ring: 'rgba(249,115,22,0.3)' },
    'Critical Issues': { color: '#f87171', bg: 'rgba(248,113,113,0.1)', ring: 'rgba(248,113,113,0.3)' },
};

const COOP_COLOR = {
    'Very cooperative': '#34d399',
    'Cooperative': '#60a5fa',
    'Somewhat difficult': '#fbbf24',
    'Difficult': '#f97316',
    'Hostile': '#f87171',
};
const DIFF_COLOR = ['', '#34d399', '#60a5fa', '#fbbf24', '#f97316', '#f87171'];
const SKILL_COLOR = { positive: '#34d399', negative: '#f87171', neutral: '#94a3b8' };
const SEV_COLOR = { critical: '#f87171', moderate: '#f97316', minor: '#fbbf24' };

function scoreColor(pct) {
    return pct >= 80 ? '#34d399' : pct >= 55 ? '#fbbf24' : '#f87171';
}
function fmtTime(s) {
    s = s || 0;
    return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`;
}

// ─── Root ─────────────────────────────────────────────────────────────────────
export default function PostCallCard({ evaluation }) {
    const [tab, setTab] = useState('summary');
    const [open, setOpen] = useState({});

    if (!evaluation) return null;

    const {
        overall_score = 0, grade = 'Developing',
        call_type, call_outcome, call_summary, call_events = [],
        caller_insights = {},
        skill_observations = [], procedure_gaps = [], strong_moments = [],
        compliance_flags = [], compliance_summary,
        missed_opportunities = [],
        recurring_risk_indicators = [], positive_indicators = [],
        agent_improvement_notes = [],
        sections = [], auto_fails = [],
        fnol_completeness_pct = 0, fnol_points_earned = 0, fnol_points_possible = 0,
        fnol_fields_collected = [], fnol_fields_missing = [],
        call_duration_seconds = 0, total_utterances = 0,
        agent_utterances = 0, customer_utterances = 0,
    } = evaluation;

    const gs = GRADE_STYLE[grade] || GRADE_STYLE['Developing'];
    const ci = caller_insights;
    const agentPct = total_utterances > 0 ? Math.round((agent_utterances / total_utterances) * 100) : 0;
    const callerPct = 100 - agentPct;
    const hasCompliance = compliance_flags.length > 0 || auto_fails.length > 0;

    const toggle = i => setOpen(p => ({ ...p, [i]: !p[i] }));

    return (
        <div className="pcc-root">

            {/* ── CRITICAL BANNERS ── */}
            {(auto_fails.length > 0 || compliance_flags.some(f => f.severity === 'critical')) && (
                <div className="pcc-banners">
                    {auto_fails.map((f, i) => (
                        <div key={i} className="pcc-banner pcc-banner--fail">
                            <span>🚨</span>
                            <div><strong>Compliance Auto-Fail</strong><p>{f}</p></div>
                        </div>
                    ))}
                    {compliance_flags.filter(f => f.severity === 'critical').map((f, i) => (
                        <div key={i} className="pcc-banner pcc-banner--fail">
                            <span>⚠️</span>
                            <div><strong>{f.flag_type}</strong><p>{f.description}</p></div>
                        </div>
                    ))}
                </div>
            )}

            {/* ── SCORE HEADER ── */}
            <div className="pcc-header">
                <div className="pcc-score-block">
                    <div className="pcc-score-ring"
                        style={{ borderColor: gs.color, boxShadow: `0 0 22px ${gs.ring}` }}>
                        <span className="pcc-score-num" style={{ color: gs.color }}>{overall_score}</span>
                        <span className="pcc-score-denom">/100</span>
                    </div>
                    <div className="pcc-grade-info">
                        <span className="pcc-grade-badge"
                            style={{ background: gs.bg, color: gs.color, border: `1px solid ${gs.color}40` }}>
                            {grade}
                        </span>
                        {call_type && <div className="pcc-call-type-label">{call_type}</div>}
                        {call_outcome && (
                            <div className="pcc-outcome-label">{call_outcome}</div>
                        )}
                    </div>
                </div>

                <div className="pcc-kpi-row">
                    <Kpi label="Duration" value={fmtTime(call_duration_seconds)} />
                    <Kpi label="Turns" value={total_utterances} />
                    <Kpi label="Agent" value={`${agentPct}%`} color="#22d3ee" />
                    <Kpi label="Caller" value={`${callerPct}%`} color="#fbbf24" />
                    <Kpi label="FNOL" value={`${fnol_completeness_pct}%`}
                        color={scoreColor(fnol_completeness_pct)} />
                    {ci.difficulty_score != null && (
                        <Kpi label="Difficulty" value={`${ci.difficulty_score}/5`}
                            color={DIFF_COLOR[ci.difficulty_score]} />
                    )}
                    {hasCompliance && (
                        <Kpi label="Compliance" value={compliance_flags.length > 0 ? `${compliance_flags.length} flag${compliance_flags.length > 1 ? 's' : ''}` : 'Auto-fail'}
                            color="#f87171" />
                    )}
                </div>
            </div>

            {/* ── TAB BAR ── */}
            <div className="pcc-tabbar">
                {TABS.map(t => (
                    <button key={t.id}
                        className={`pcc-tab ${tab === t.id ? 'pcc-tab--on' : ''}`}
                        onClick={() => setTab(t.id)}
                        style={tab === t.id ? { '--tc': gs.color } : {}}>
                        <span>{t.icon}</span> {t.label}
                    </button>
                ))}
            </div>

            {/* ── BODY ── */}
            <div className="pcc-body">


                {/* ═══════════════════ CALL SUMMARY ═══════════════════ */}
                {tab === 'summary' && (
                    <div className="pcc-tab-content">

                        {/* Caller profile */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">🗣️ Caller Profile</h3>
                            <div className="pcc-caller-layout">
                                <div className="pcc-caller-fields">
                                    <F label="Who Called" v={ci.caller_description} />
                                    <F label="Emotional State" v={ci.emotional_state} />
                                    <F label="Communication" v={ci.communication_style} />
                                    <F label="Cooperation">
                                        <span style={{ color: COOP_COLOR[ci.cooperation_level] || '#94a3b8', fontWeight: 600 }}>
                                            {ci.cooperation_level}
                                        </span>
                                    </F>
                                </div>

                                {ci.difficulty_score != null && (
                                    <div className="pcc-diff-panel">
                                        <div className="pcc-diff-row">
                                            <span className="pcc-label-xs">Call Difficulty</span>
                                            <div className="pcc-diff-dots">
                                                {[1, 2, 3, 4, 5].map(n => (
                                                    <span key={n} className="pcc-diff-pip"
                                                        style={{
                                                            background: n <= ci.difficulty_score
                                                                ? DIFF_COLOR[ci.difficulty_score]
                                                                : 'rgba(255,255,255,0.1)'
                                                        }} />
                                                ))}
                                            </div>
                                            <span style={{ color: DIFF_COLOR[ci.difficulty_score], fontWeight: 700, fontSize: '0.82rem' }}>
                                                {ci.difficulty_score}/5
                                            </span>
                                        </div>
                                        <p className="pcc-text-dim">{ci.difficulty_rationale}</p>
                                        {ci.notable_behaviors?.length > 0 && (
                                            <div className="pcc-tag-row">
                                                {ci.notable_behaviors.map((b, i) => (
                                                    <span key={i} className="pcc-tag pcc-tag--amber">{b}</span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </section>

                        {/* Call narrative */}
                        {call_summary && (
                            <section className="pcc-card-block">
                                <h3 className="pcc-sh">📝 Call Narrative</h3>
                                {call_summary.split('\n').filter(p => p.trim()).map((p, i) => (
                                    <p key={i} className="pcc-prose">{p}</p>
                                ))}
                            </section>
                        )}

                        {/* Talk distribution */}
                        <section className="pcc-card-block pcc-card-block--compact">
                            <div className="pcc-talk-header">
                                <span className="pcc-sh" style={{ margin: 0 }}>Talk Distribution</span>
                                <span className="pcc-text-dim pcc-text-sm">
                                    <span className="pcc-dot" style={{ background: '#22d3ee' }} />
                                    Agent {agentPct}% ({agent_utterances} turns)
                                    &nbsp;&nbsp;
                                    <span className="pcc-dot" style={{ background: '#fbbf24' }} />
                                    Caller {callerPct}% ({customer_utterances} turns)
                                </span>
                            </div>
                            <div className="pcc-talkbar">
                                <div style={{ width: `${agentPct}%`, background: '#22d3ee', height: '100%' }} />
                                <div style={{ width: `${callerPct}%`, background: '#fbbf24', height: '100%' }} />
                            </div>
                        </section>

                        {/* Key events timeline */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">📌 Call Events</h3>
                            {call_events.length > 0 ? (
                                <div className="pcc-events">
                                    {call_events.map((e, i) => (
                                        <div key={i} className="pcc-event">
                                            <div className="pcc-event-num"
                                                style={{ background: gs.bg, color: gs.color, borderColor: gs.color + '40' }}>
                                                {i + 1}
                                            </div>
                                            <div className="pcc-event-connector" />
                                            <p className="pcc-event-text">{e}</p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No notable call events were detected during this interaction.</p>
                            )}
                        </section>

                        {/* FNOL completeness */}
                        <section className="pcc-card-block">
                            <div className="pcc-fnol-hdr">
                                <div>
                                    <h3 className="pcc-sh" style={{ margin: 0 }}>FNOL Data Collected</h3>
                                    <p className="pcc-text-dim pcc-text-sm">
                                        {fnol_fields_collected.length} / {fnol_fields_collected.length + fnol_fields_missing.length} fields
                                    </p>
                                </div>
                                <span className="pcc-fnol-pct" style={{ color: scoreColor(fnol_completeness_pct) }}>
                                    {fnol_completeness_pct}%
                                    <span className="pcc-text-dim" style={{ fontSize: '0.68rem', fontWeight: 400 }}>
                                        &nbsp;({fnol_points_earned}/{fnol_points_possible} pts)
                                    </span>
                                </span>
                            </div>
                            <div className="pcc-progress-track">
                                <div className="pcc-progress-fill"
                                    style={{ width: `${fnol_completeness_pct}%`, background: scoreColor(fnol_completeness_pct) }} />
                            </div>
                            <div className="pcc-fnol-grid">
                                {fnol_fields_collected.map((f, i) => (
                                    <div key={i} className="pcc-fnol-row pcc-fnol-row--ok">
                                        <span>✅</span>
                                        <div>
                                            <div className="pcc-fnol-name">{f.field}</div>
                                            <div className="pcc-text-dim pcc-text-sm">{f.value}</div>
                                        </div>
                                        <span className="pcc-pts-badge pcc-pts-badge--ok">+{f.points}</span>
                                    </div>
                                ))}
                                {fnol_fields_missing.map((f, i) => (
                                    <div key={i} className="pcc-fnol-row pcc-fnol-row--miss">
                                        <span>❌</span>
                                        <div>
                                            <div className="pcc-fnol-name">{f.field}</div>
                                            <div className="pcc-text-dim pcc-text-sm">Not collected</div>
                                        </div>
                                        <span className="pcc-pts-badge pcc-pts-badge--miss">0/{f.points}</span>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>
                )}


                {/* ═══════════════════ AGENT INSIGHTS ═══════════════════ */}
                {tab === 'insights' && (
                    <div className="pcc-tab-content">

                        {/* Section score bars */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">Score by Section</h3>
                            {sections.map((sec, i) => {
                                const pct = sec.points_possible > 0
                                    ? Math.round((sec.points_awarded / sec.points_possible) * 100) : 0;
                                const c = sec.auto_failed ? '#f87171' : scoreColor(pct);
                                return (
                                    <div key={i} className="pcc-sec-row">
                                        <div className="pcc-sec-name">
                                            {sec.auto_failed && <span className="pcc-chip pcc-chip--fail">FAIL</span>}
                                            {sec.section_name}
                                        </div>
                                        <div className="pcc-sec-track">
                                            <div className="pcc-sec-fill" style={{ width: `${pct}%`, background: c }} />
                                        </div>
                                        <span className="pcc-sec-pts" style={{ color: c }}>
                                            {sec.points_awarded}/{sec.points_possible}
                                        </span>
                                    </div>
                                );
                            })}
                        </section>

                        {/* Skill observations */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">Skill Observations</h3>
                            {skill_observations.length > 0 ? (
                                <div className="pcc-observations">
                                    {skill_observations.map((obs, i) => (
                                        <div key={i} className={`pcc-obs pcc-obs--${obs.valence}`}>
                                            <div className="pcc-obs-top">
                                                <span className="pcc-obs-area"
                                                    style={{ color: SKILL_COLOR[obs.valence] || '#94a3b8' }}>
                                                    {obs.valence === 'positive' ? '✓' : obs.valence === 'negative' ? '✗' : '·'} {obs.skill_area}
                                                </span>
                                            </div>
                                            <p className="pcc-obs-text">{obs.observation}</p>
                                            <p className="pcc-obs-impact">↳ {obs.impact}</p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No specific skill observations generated for this call.</p>
                            )}
                        </section>

                        {/* Strong moments + Procedure gaps side-by-side */}
                        <div className="pcc-2up">
                            <section className="pcc-card-block">
                                <h3 className="pcc-sh" style={{ color: '#34d399' }}>⭐ Strong Moments</h3>
                                {strong_moments.length > 0 ? (
                                    <ul className="pcc-insight-list">
                                        {strong_moments.map((m, i) => (
                                            <li key={i} className="pcc-insight-item pcc-insight-item--pos">{m}</li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No strong moments were identified.</p>
                                )}
                            </section>
                            <section className="pcc-card-block">
                                <h3 className="pcc-sh" style={{ color: '#f97316' }}>⚠ Procedure Gaps</h3>
                                {procedure_gaps.length > 0 ? (
                                    <ul className="pcc-insight-list">
                                        {procedure_gaps.map((g, i) => (
                                            <li key={i} className="pcc-insight-item pcc-insight-item--neg">{g}</li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No procedure gaps were identified.</p>
                                )}
                            </section>
                        </div>

                        {/* Pattern indicators (supervisor-facing) */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">Pattern Indicators
                                <span className="pcc-sh-sub">Tracked across calls for supervisor review</span>
                            </h3>
                            {(recurring_risk_indicators.length > 0 || positive_indicators.length > 0) ? (
                                <div className="pcc-2up">
                                    {positive_indicators.length > 0 && (
                                        <div>
                                            <div className="pcc-label-xs" style={{ color: '#34d399', marginBottom: 8 }}>Positive</div>
                                            {positive_indicators.map((p, i) => (
                                                <div key={i} className="pcc-indicator pcc-indicator--pos">
                                                    <span>↑</span> {p}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    {recurring_risk_indicators.length > 0 && (
                                        <div>
                                            <div className="pcc-label-xs" style={{ color: '#f97316', marginBottom: 8 }}>Risk Patterns</div>
                                            {recurring_risk_indicators.map((r, i) => (
                                                <div key={i} className="pcc-indicator pcc-indicator--risk">
                                                    <span>↓</span> {r}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No recurring behavioral patterns have been identified yet.</p>
                            )}
                        </section>
                    </div>
                )}


                {/* ═══════════════════ QA SCORECARD ═══════════════════ */}
                {tab === 'scorecard' && (
                    <div className="pcc-tab-content">
                        {sections.map((sec, idx) => {
                            const pct = sec.points_possible > 0
                                ? Math.round((sec.points_awarded / sec.points_possible) * 100) : 0;
                            const c = sec.auto_failed ? '#f87171' : scoreColor(pct);
                            const isOpen = open[idx];
                            return (
                                <div key={idx} className={`pcc-qa-sec ${sec.auto_failed ? 'pcc-qa-sec--fail' : ''}`}>
                                    <button className="pcc-qa-hdr" onClick={() => toggle(idx)}>
                                        <div className="pcc-qa-left">
                                            <span className="pcc-chevron">{isOpen ? '▾' : '▸'}</span>
                                            <span className="pcc-qa-title">{sec.section_name}</span>
                                            {sec.auto_failed && <span className="pcc-chip pcc-chip--fail">AUTO-FAIL</span>}
                                        </div>
                                        <div className="pcc-qa-right">
                                            <span style={{ color: c, fontWeight: 800, fontSize: '0.82rem' }}>
                                                {sec.points_awarded}/{sec.points_possible}
                                            </span>
                                            <div className="pcc-mini-bar">
                                                <div style={{ width: `${pct}%`, height: '100%', background: c, borderRadius: 3 }} />
                                            </div>
                                        </div>
                                    </button>
                                    {isOpen && (
                                        <div className="pcc-qa-body">
                                            {sec.auto_failed && sec.auto_fail_reason && (
                                                <div className="pcc-autofail-note">🚨 {sec.auto_fail_reason}</div>
                                            )}
                                            {sec.rubric_items.map((item, j) => (
                                                <div key={j} className={`pcc-ri ${item.passed ? 'pcc-ri--pass' : 'pcc-ri--fail'}`}>
                                                    <div className="pcc-ri-top">
                                                        <span>{item.passed ? '✅' : '❌'}</span>
                                                        <span className="pcc-ri-criterion">{item.criterion}</span>
                                                        <span style={{ fontWeight: 700, fontSize: '0.78rem', color: item.passed ? '#34d399' : '#f87171', marginLeft: 'auto', flexShrink: 0 }}>
                                                            {item.points_awarded}/{item.points_possible}
                                                        </span>
                                                    </div>
                                                    {item.evidence && item.evidence !== 'Not observed in transcript' && (
                                                        <div className="pcc-evidence">
                                                            <span className="pcc-ev-label">Agent said:</span> "{item.evidence}"
                                                        </div>
                                                    )}
                                                    {item.evidence === 'Not observed in transcript' && !item.passed && (
                                                        <div className="pcc-absent">Not observed in transcript</div>
                                                    )}
                                                    {item.deduction_reason && (
                                                        <div className="pcc-deduction">⚠ {item.deduction_reason}</div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}


                {/* ═══════════════════ IMPROVEMENT ═══════════════════ */}
                {tab === 'improvement' && (
                    <div className="pcc-tab-content">

                        {/* Compliance section */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">🔒 Compliance
                                {compliance_summary && (
                                    <span className="pcc-sh-sub"
                                        style={{ color: compliance_flags.length === 0 && auto_fails.length === 0 ? '#34d399' : '#f87171' }}>
                                        {compliance_summary}
                                    </span>
                                )}
                            </h3>
                            {compliance_flags.length === 0 && auto_fails.length === 0 ? (
                                <div className="pcc-ok-note">✅ No compliance issues identified in this call.</div>
                            ) : (
                                <div className="pcc-compliance-list">
                                    {compliance_flags.map((f, i) => (
                                        <div key={i} className="pcc-cflag"
                                            style={{ borderLeftColor: SEV_COLOR[f.severity] || '#94a3b8' }}>
                                            <div className="pcc-cflag-top">
                                                <span className="pcc-chip"
                                                    style={{
                                                        background: SEV_COLOR[f.severity] + '20',
                                                        color: SEV_COLOR[f.severity],
                                                        borderColor: SEV_COLOR[f.severity] + '40'
                                                    }}>
                                                    {f.severity.toUpperCase()}
                                                </span>
                                                <span className="pcc-cflag-type">{f.flag_type}</span>
                                            </div>
                                            <p className="pcc-prose pcc-prose--sm">{f.description}</p>
                                            {f.agent_quote && f.agent_quote !== 'Not said — omission' && (
                                                <div className="pcc-evidence">
                                                    <span className="pcc-ev-label">Agent said:</span> "{f.agent_quote}"
                                                </div>
                                            )}
                                            {f.agent_quote === 'Not said — omission' && (
                                                <div className="pcc-absent">Omission — not said in transcript</div>
                                            )}
                                            <div className="pcc-risk-note">⚖ {f.risk}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* Missed opportunities */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">💡 Missed Opportunities</h3>
                            {missed_opportunities.length > 0 ? (
                                <div className="pcc-mo-list">
                                    {missed_opportunities.map((mo, i) => (
                                        <div key={i} className="pcc-mo">
                                            <div className="pcc-mo-when">📍 {mo.moment}</div>
                                            <div className="pcc-mo-body">
                                                <div className="pcc-mo-row">
                                                    <span className="pcc-label-xs" style={{ color: '#94a3b8' }}>What happened</span>
                                                    <p className="pcc-prose pcc-prose--sm">{mo.what_happened}</p>
                                                </div>
                                                <div className="pcc-mo-row pcc-mo-row--better">
                                                    <span className="pcc-label-xs" style={{ color: '#60a5fa' }}>Better approach</span>
                                                    <p className="pcc-prose pcc-prose--sm">{mo.better_approach}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No missed opportunities were detected.</p>
                            )}
                        </section>

                        {/* Agent improvement notes */}
                        <section className="pcc-card-block">
                            <h3 className="pcc-sh">📝 Notes for the Agent
                                <span className="pcc-sh-sub">Specific to this call</span>
                            </h3>
                            {agent_improvement_notes.length > 0 ? (
                                <div className="pcc-improve-list">
                                    {agent_improvement_notes.map((note, i) => (
                                        <div key={i} className="pcc-improve-note">
                                            <span className="pcc-improve-num">{i + 1}</span>
                                            <p className="pcc-prose pcc-prose--sm">{note}</p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="pcc-text-dim pcc-text-sm" style={{ fontStyle: 'italic', marginTop: '10px' }}>No specific improvement notes for this interaction.</p>
                            )}
                        </section>
                    </div>
                )}

            </div>
        </div>
    );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function Kpi({ label, value, color }) {
    return (
        <div className="pcc-kpi">
            <span className="pcc-kpi-v" style={color ? { color } : {}}>{value}</span>
            <span className="pcc-kpi-l">{label}</span>
        </div>
    );
}

function F({ label, v, children }) {
    return (
        <div className="pcc-f">
            <span className="pcc-f-label">{label}</span>
            <span className="pcc-f-val">{children || v || '—'}</span>
        </div>
    );
}