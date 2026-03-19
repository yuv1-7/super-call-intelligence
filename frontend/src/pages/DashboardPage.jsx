// pages/DashboardPage.jsx — Premium role-aware dashboard with charts

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import { motion } from 'framer-motion';
import {
    PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
    Tooltip, ResponsiveContainer
} from 'recharts';
import {
    Phone, TrendingUp, Award, Activity, ArrowRight,
    BarChart3, Users, Clock, Zap, Target, ChevronRight
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

    return (
        <motion.div className="dashboard-page" {...fadeIn}>
            {/* Welcome Header */}
            <div className="page-header">
                <div className="page-header-info">
                    <h1 className="page-title">Welcome back, {userName}</h1>
                    <p className="page-subtitle">{roleTitle}</p>
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
                    <div className="dash-card">
                        <div className="dash-card-header">
                            <h3><BarChart3 size={16} /> Grade Distribution</h3>
                        </div>
                        <div className="dash-card-body chart-container">
                            {userRole === 'agent' ? (
                                <ResponsiveContainer width="100%" height={220}>
                                    <PieChart>
                                        <Pie
                                            data={gradeData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={55}
                                            outerRadius={85}
                                            paddingAngle={3}
                                            dataKey="value"
                                            stroke="none"
                                        >
                                            {gradeData.map((entry, idx) => (
                                                <Cell key={idx} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{
                                                background: '#1e293b',
                                                border: '1px solid rgba(255,255,255,0.1)',
                                                borderRadius: '8px',
                                                color: '#f1f5f9',
                                                fontSize: '0.82rem',
                                            }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : (
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={gradeData} layout="vertical" barSize={16}>
                                        <XAxis type="number" hide />
                                        <YAxis
                                            type="category"
                                            dataKey="name"
                                            width={120}
                                            tick={{ fill: '#94a3b8', fontSize: 12 }}
                                            axisLine={false}
                                            tickLine={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                background: '#1e293b',
                                                border: '1px solid rgba(255,255,255,0.1)',
                                                borderRadius: '8px',
                                                color: '#f1f5f9',
                                                fontSize: '0.82rem',
                                            }}
                                        />
                                        <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                                            {gradeData.map((entry, idx) => (
                                                <Cell key={idx} fill={entry.color} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            )}
                            <div className="grade-legend">
                                {gradeData.map(g => (
                                    <div key={g.name} className="grade-legend-item">
                                        <span className="grade-dot" style={{ background: g.color }} />
                                        <span className="grade-legend-label">{g.name}</span>
                                        <span className="grade-legend-count">{g.value}</span>
                                    </div>
                                ))}
                            </div>
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
