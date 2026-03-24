// pages/DashboardPage.jsx — Premium role-aware dashboard with charts

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import { motion } from 'framer-motion';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer
} from 'recharts';
import {
    Phone, TrendingUp, Award, Activity,
    BarChart3, Users, Clock, ChevronRight
} from 'lucide-react';

const GRADE_COLORS = {
    'Exceptional': '#34d399',
    'Proficient': '#60a5fa',
    'Developing': '#fbbf24',
    'Needs Improvement': '#f97316',
    'Critical Issues': '#ef4444',
};

const GRADE_ORDER = ['Exceptional', 'Proficient', 'Developing', 'Needs Improvement', 'Critical Issues'];

const fadeIn = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4 }
};

export default function DashboardPage({ userRole, userName }) {
    const navigate = useNavigate();
    const { fetchWithAuth } = useApi();
    const [summary, setSummary] = useState(null);
    const [recentCalls, setRecentCalls] = useState([]);
    const [teamData, setTeamData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadDashboardData();
    }, []);

    async function loadDashboardData() {
        setLoading(true);
        try {
            const [summaryRes, callsRes] = await Promise.all([
                fetchWithAuth('/api/evaluations/summary'),
                fetchWithAuth('/api/calls?limit=5'),
            ]);
            setSummary(summaryRes);
            setRecentCalls(callsRes.calls || []);

            if (userRole === 'team_lead' || userRole === 'manager') {
                const teamRes = await fetchWithAuth('/api/team/members');
                setTeamData(teamRes);
            }
        } catch (err) {
            console.error('Dashboard load failed:', err);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="page-loading">
                <div className="loading-spinner" />
                <p>Loading dashboard…</p>
            </div>
        );
    }

    // Prepare grade distribution chart data
    const gradeData = summary?.grade_distribution
        ? GRADE_ORDER
            .filter(g => summary.grade_distribution[g])
            .map(g => ({
                name: g,
                value: summary.grade_distribution[g],
                color: GRADE_COLORS[g],
            }))
        : [];

    const totalCalls = summary?.total_calls || 0;
    const avgScore = summary?.avg_score || 0;
    const maxScore = summary?.max_score ?? '—';
    const minScore = summary?.min_score ?? '—';

    const roleTitle = userRole === 'manager'
        ? 'Organization Overview'
        : userRole === 'team_lead'
            ? 'Team Dashboard'
            : 'My Performance';

    const greeting = (() => {
        const h = new Date().getHours();
        if (h < 12) return 'Good morning';
        if (h < 17) return 'Good afternoon';
        return 'Good evening';
    })();

    return (
        <motion.div className="dashboard-page" {...fadeIn}>
            {/* Welcome Header */}
            <div className="page-header">
                <div className="page-header-info">
                    <h1 className="page-title">{greeting}, <span className="gradient-name">{userName}</span></h1>
                    <p className="page-subtitle">{roleTitle} • {new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}</p>
                </div>
                {userRole !== 'manager' && (
                    <button className="btn-primary" onClick={() => navigate('/call')}>
                        <Phone size={16} />
                        <span>Start New Call</span>
                    </button>
                )}
            </div>

            {/* KPI Cards */}
            <div className="kpi-grid">
                <KpiCard
                    icon={<Phone size={20} />}
                    iconClass="kpi-icon--blue"
                    label="Total Calls"
                    value={totalCalls}
                />
                <KpiCard
                    icon={<TrendingUp size={20} />}
                    iconClass="kpi-icon--green"
                    label="Avg Score"
                    value={avgScore}
                    suffix="/100"
                />
                <KpiCard
                    icon={<Award size={20} />}
                    iconClass="kpi-icon--amber"
                    label="Best Score"
                    value={maxScore}
                />
                <KpiCard
                    icon={<Activity size={20} />}
                    iconClass="kpi-icon--red"
                    label="Lowest Score"
                    value={minScore}
                />
            </div>

            <div className="dashboard-grid">
                {/* Grade Distribution */}
                {gradeData.length > 0 && (
                    <div className="dash-card dash-card--wide">
                        <div className="dash-card-header">
                            <h3><BarChart3 size={16} /> Grade Distribution</h3>
                            <span className="grade-total-badge">{totalCalls} total</span>
                        </div>
                        <div className="dash-card-body chart-container">
                            {userRole === 'agent' ? (
                                /* Agent: Donut chart */
                                <div className="donut-wrapper">
                                    <ResponsiveContainer width="100%" height={200}>
                                        <PieChart>
                                            <Pie
                                                data={gradeData}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={58}
                                                outerRadius={88}
                                                paddingAngle={3}
                                                dataKey="value"
                                                stroke="none"
                                                startAngle={90}
                                                endAngle={-270}
                                            >
                                                {gradeData.map((entry, idx) => (
                                                    <Cell key={idx} fill={entry.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip
                                                contentStyle={{
                                                    background: 'rgba(15,23,42,0.95)',
                                                    border: '1px solid rgba(255,255,255,0.08)',
                                                    borderRadius: '10px',
                                                    color: '#f1f5f9',
                                                    fontSize: '0.82rem',
                                                    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                                                    padding: '8px 14px',
                                                }}
                                                formatter={(value, name) => [
                                                    <span style={{ fontWeight: 700 }}>{value} calls</span>,
                                                    name
                                                ]}
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                            ) : (
                                /* Manager/Lead: Custom horizontal bar chart */
                                <div className="grade-bars-custom">
                                    {gradeData.map((g, idx) => {
                                        const maxVal = Math.max(...gradeData.map(d => d.value));
                                        const pct = maxVal > 0 ? (g.value / maxVal) * 100 : 0;
                                        return (
                                            <motion.div
                                                key={g.name}
                                                className="grade-bar-row"
                                                initial={{ opacity: 0, x: -16 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: idx * 0.07, duration: 0.35 }}
                                            >
                                                <div className="grade-bar-label-col">
                                                    <span className="grade-bar-dot" style={{ background: g.color }} />
                                                    <span className="grade-bar-name">{g.name}</span>
                                                </div>
                                                <div className="grade-bar-track-col">
                                                    <div className="grade-bar-track-bg">
                                                        <motion.div
                                                            className="grade-bar-track-fill"
                                                            style={{ background: g.color }}
                                                            initial={{ width: 0 }}
                                                            animate={{ width: `${pct}%` }}
                                                            transition={{ delay: idx * 0.07 + 0.15, duration: 0.5, ease: 'easeOut' }}
                                                        />
                                                    </div>
                                                </div>
                                                <div className="grade-bar-count-col">
                                                    <span className="grade-bar-count" style={{ color: g.color }}>{g.value}</span>
                                                    <span className="grade-bar-pct">{totalCalls > 0 ? Math.round((g.value / totalCalls) * 100) : 0}%</span>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            )}
                            {/* Legend for donut (agent view) */}
                            {userRole === 'agent' && (
                                <div className="grade-legend">
                                    {gradeData.map(g => (
                                        <div key={g.name} className="grade-legend-item">
                                            <span className="grade-dot" style={{ background: g.color }} />
                                            <span className="grade-legend-label">{g.name}</span>
                                            <span className="grade-legend-count">{g.value}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Team Performance (Lead / Manager only) */}
                {teamData?.agents && teamData.agents.length > 0 && (
                    <div className="dash-card">
                        <div className="dash-card-header">
                            <h3><Users size={16} /> {userRole === 'manager' ? 'Agent Overview' : 'Team Performance'}</h3>
                            <button className="btn-link-sm" onClick={() => navigate('/team')}>
                                View All <ChevronRight size={14} />
                            </button>
                        </div>
                        <div className="dash-card-body">
                            <div className="agent-perf-list">
                                {teamData.agents.slice(0, 5).map((agent, idx) => (
                                    <div key={agent.clerk_user_id} className="agent-perf-row">
                                        <div className="agent-perf-rank">{idx + 1}</div>
                                        <div className="agent-perf-info">
                                            <span className="agent-perf-name">{agent.name}</span>
                                            <span className="agent-perf-calls">{agent.total_calls} calls</span>
                                        </div>
                                        <div className="agent-perf-score-group">
                                            <div className="agent-perf-bar-track">
                                                <div
                                                    className="agent-perf-bar-fill"
                                                    style={{
                                                        width: `${Math.min(agent.avg_score, 100)}%`,
                                                        background: agent.avg_score >= 75 ? '#34d399'
                                                            : agent.avg_score >= 60 ? '#fbbf24'
                                                                : '#ef4444',
                                                    }}
                                                />
                                            </div>
                                            <span className="agent-perf-score" style={{
                                                color: agent.avg_score >= 75 ? '#34d399'
                                                    : agent.avg_score >= 60 ? '#fbbf24'
                                                        : '#ef4444'
                                            }}>
                                                {agent.avg_score}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Recent Calls */}
                <div className="dash-card dash-card--wide">
                    <div className="dash-card-header">
                        <h3><Clock size={16} /> Recent Calls</h3>
                        <button className="btn-link-sm" onClick={() => navigate('/history')}>
                            View All <ChevronRight size={14} />
                        </button>
                    </div>
                    <div className="dash-card-body">
                        {recentCalls.length === 0 ? (
                            <div className="empty-state">
                                <Phone size={32} />
                                <p>No calls yet. Start your first call!</p>
                            </div>
                        ) : (
                            <div className="recent-calls-table">
                                {recentCalls.map(call => (
                                    <div
                                        key={call.id}
                                        className="recent-call-row"
                                        onClick={() => navigate(`/history/${call.id}`)}
                                    >
                                        <div className="recent-call-info">
                                            <span className="recent-call-intent">
                                                {call.intent?.replace(/_/g, ' ') || 'Unknown'}
                                            </span>
                                            <span className="recent-call-meta">
                                                {call.start_time
                                                    ? new Date(call.start_time).toLocaleDateString(undefined, {
                                                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                                    })
                                                    : '—'}
                                                {userRole !== 'agent' && call.agent_name && ` • ${call.agent_name}`}
                                            </span>
                                        </div>
                                        <div className="recent-call-score" style={{
                                            '--score-color': call.overall_score >= 75 ? '#34d399'
                                                : call.overall_score >= 60 ? '#fbbf24'
                                                    : '#ef4444'
                                        }}>
                                            {call.overall_score ?? '—'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Bottom spacer for scroll breathing room */}
            <div style={{ height: '24px' }} />
        </motion.div>
    );
}

function KpiCard({ icon, iconClass, label, value, suffix }) {
    return (
        <motion.div
            className="kpi-card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            <div className={`kpi-card-icon ${iconClass}`}>{icon}</div>
            <div className="kpi-card-data">
                <span className="kpi-card-value">
                    {value}{suffix && <small>{suffix}</small>}
                </span>
                <span className="kpi-card-label">{label}</span>
            </div>
        </motion.div>
    );
}
