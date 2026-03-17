// pages/DashboardPage.jsx — Role-aware landing page

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import {
    Phone, TrendingUp, Award, Clock, AlertTriangle,
    ArrowRight, BarChart3, Users, Activity
} from 'lucide-react';

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

    function getGradeColor(grade) {
        const colors = {
            'Exceptional': '#10b981',
            'Proficient': '#3b82f6',
            'Developing': '#f59e0b',
            'Needs Improvement': '#f97316',
            'Critical Issues': '#ef4444',
        };
        return colors[grade] || '#64748b';
    }

    if (loading) {
        return (
            <div className="dashboard-loading">
                <div className="loading-spinner" />
                <p>Loading dashboard...</p>
            </div>
        );
    }

    return (
        <div className="dashboard-page">
            {/* Welcome Header */}
            <div className="dashboard-welcome">
                <div>
                    <h1>Welcome back, {userName || 'User'}</h1>
                    <p className="welcome-subtitle">
                        {userRole === 'manager' ? 'Organization Overview' :
                         userRole === 'team_lead' ? 'Team Dashboard' :
                         'Your Performance Dashboard'}
                    </p>
                </div>
                {(userRole === 'agent' || userRole === 'team_lead') && (
                    <button className="btn-start-call" onClick={() => navigate('/call')}>
                        <Phone size={18} />
                        Start New Call
                    </button>
                )}
                {userRole === 'manager' && (
                    <button className="btn-start-call emergency" onClick={() => navigate('/call')}>
                        <AlertTriangle size={18} />
                        Emergency Call
                    </button>
                )}
            </div>

            {/* Stats Cards */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon calls">
                        <Phone size={22} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{summary?.total_calls || 0}</span>
                        <span className="stat-label">Total Calls</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon score">
                        <TrendingUp size={22} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{summary?.avg_score || 0}</span>
                        <span className="stat-label">Avg Score</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon best">
                        <Award size={22} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{summary?.max_score ?? '—'}</span>
                        <span className="stat-label">Best Score</span>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon low">
                        <Activity size={22} />
                    </div>
                    <div className="stat-content">
                        <span className="stat-value">{summary?.min_score ?? '—'}</span>
                        <span className="stat-label">Lowest Score</span>
                    </div>
                </div>
            </div>

            {/* Grade Distribution */}
            {summary?.grade_distribution && Object.keys(summary.grade_distribution).length > 0 && (
                <div className="dashboard-card grade-dist-card">
                    <h3><BarChart3 size={18} /> Grade Distribution</h3>
                    <div className="grade-bars">
                        {Object.entries(summary.grade_distribution).map(([grade, count]) => (
                            <div key={grade} className="grade-bar-item">
                                <span className="grade-label" style={{ color: getGradeColor(grade) }}>
                                    {grade}
                                </span>
                                <div className="grade-bar-track">
                                    <div
                                        className="grade-bar-fill"
                                        style={{
                                            width: `${Math.min((count / summary.total_calls) * 100, 100)}%`,
                                            backgroundColor: getGradeColor(grade),
                                        }}
                                    />
                                </div>
                                <span className="grade-count">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Team Performance (Lead / Manager only) */}
            {teamData?.agents && teamData.agents.length > 0 && (
                <div className="dashboard-card team-card">
                    <div className="card-header-row">
                        <h3><Users size={18} /> {userRole === 'manager' ? 'All Agents' : 'Team Performance'}</h3>
                        <button className="btn-link" onClick={() => navigate('/team')}>
                            View All <ArrowRight size={14} />
                        </button>
                    </div>
                    <div className="team-table">
                        <div className="team-row header">
                            <span>Agent</span>
                            <span>Calls</span>
                            <span>Avg Score</span>
                        </div>
                        {teamData.agents.slice(0, 5).map(agent => (
                            <div key={agent.clerk_user_id} className="team-row">
                                <span className="agent-name">{agent.name}</span>
                                <span>{agent.total_calls}</span>
                                <span className="agent-score" style={{
                                    color: agent.avg_score >= 75 ? '#10b981' :
                                           agent.avg_score >= 60 ? '#f59e0b' : '#ef4444'
                                }}>
                                    {agent.avg_score}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recent Calls */}
            <div className="dashboard-card recent-card">
                <div className="card-header-row">
                    <h3><Clock size={18} /> Recent Calls</h3>
                    <button className="btn-link" onClick={() => navigate('/history')}>
                        View All <ArrowRight size={14} />
                    </button>
                </div>
                {recentCalls.length === 0 ? (
                    <p className="empty-state">No calls yet. Start your first call!</p>
                ) : (
                    <div className="recent-calls-list">
                        {recentCalls.map(call => (
                            <div
                                key={call.id}
                                className="recent-call-item"
                                onClick={() => navigate(`/history/${call.id}`)}
                            >
                                <div className="call-info">
                                    <span className="call-intent">{call.intent?.replace(/_/g, ' ') || 'Unknown'}</span>
                                    <span className="call-time">
                                        {call.start_time ? new Date(call.start_time).toLocaleDateString() : '—'}
                                    </span>
                                    {userRole !== 'agent' && call.agent_name && (
                                        <span className="call-agent">{call.agent_name}</span>
                                    )}
                                </div>
                                <div className="call-score-badge" style={{
                                    backgroundColor: call.overall_score >= 75 ? 'rgba(16,185,129,0.15)' :
                                                     call.overall_score >= 60 ? 'rgba(245,158,11,0.15)' :
                                                     'rgba(239,68,68,0.15)',
                                    color: call.overall_score >= 75 ? '#10b981' :
                                           call.overall_score >= 60 ? '#f59e0b' : '#ef4444',
                                }}>
                                    {call.overall_score ?? '—'}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
