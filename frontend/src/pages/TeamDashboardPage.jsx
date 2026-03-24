// pages/TeamDashboardPage.jsx — Team overview with agent drill-down

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import {
    Users, TrendingUp, Award, BarChart3, ChevronDown, ChevronUp,
    Phone, Clock, ArrowLeft, Target, User, PhoneOff, UserX
} from 'lucide-react';

export default function TeamDashboardPage({ userRole }) {
    const navigate = useNavigate();
    const { fetchWithAuth } = useApi();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expandedAgent, setExpandedAgent] = useState(null);
    const [agentCalls, setAgentCalls] = useState({});
    const [loadingAgent, setLoadingAgent] = useState(null);
    const [selectedTeam, setSelectedTeam] = useState(null);
    const [teamAgents, setTeamAgents] = useState(null);
    const [loadingTeam, setLoadingTeam] = useState(false);

    useEffect(() => {
        loadTeamData();
    }, []);

    async function loadTeamData() {
        setLoading(true);
        try {
            const [teamRes, perfRes] = await Promise.all([
                fetchWithAuth('/api/team/members'),
                fetchWithAuth('/api/team/performance'),
            ]);
            setData({ ...teamRes, performance: perfRes.agents || [] });
        } catch (err) {
            console.error('Failed to load team data:', err);
        } finally {
            setLoading(false);
        }
    }

    async function selectTeam(team) {
        if (selectedTeam?.id === team.id) return;
        setSelectedTeam(team);
        setExpandedAgent(null);
        setLoadingTeam(true);
        try {
            const perfRes = await fetchWithAuth(`/api/team/performance?team_id=${encodeURIComponent(team.id)}`);
            setTeamAgents(perfRes.agents || []);
        } catch (err) {
            console.error('Failed to load team performance:', err);
            setTeamAgents([]);
        } finally {
            setLoadingTeam(false);
        }
    }

    function goBackToAll() {
        setSelectedTeam(null);
        setTeamAgents(null);
        setExpandedAgent(null);
    }

    async function toggleAgentDetail(clerkId) {
        if (expandedAgent === clerkId) {
            setExpandedAgent(null);
            return;
        }
        setExpandedAgent(clerkId);

        if (!agentCalls[clerkId]) {
            setLoadingAgent(clerkId);
            try {
                const res = await fetchWithAuth(`/api/team/agent/${clerkId}/calls`);
                setAgentCalls(prev => ({ ...prev, [clerkId]: res }));
            } catch (err) {
                console.error('Failed to load agent calls:', err);
                setAgentCalls(prev => ({ ...prev, [clerkId]: { calls: [], summary: {} } }));
            } finally {
                setLoadingAgent(null);
            }
        }
    }

    function getScoreColor(score) {
        if (score >= 75) return '#34d399';
        if (score >= 60) return '#fbbf24';
        return '#ef4444';
    }

    if (loading) {
        return (
            <div className="page-loading">
                <div className="loading-spinner" />
                <p>Loading team data…</p>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="empty-state-large">
                <Users size={48} />
                <h3>Unable to load team data</h3>
            </div>
        );
    }

    // When a team is selected, show filtered agents; otherwise show all
    const agents = selectedTeam ? (teamAgents || []) : (data.performance || data.agents || []);

    // Team summary stats
    const teamAvg = agents.length > 0
        ? Math.round(agents.reduce((sum, a) => sum + a.avg_score, 0) / agents.length)
        : 0;
    const teamTotalCalls = agents.reduce((sum, a) => sum + a.total_calls, 0);
    const topAgent = agents.length > 0 ? agents[0] : null;

    return (
        <motion.div
            className="team-page"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            {/* Header */}
            <div className="page-header">
                <div className="page-header-info">
                    {selectedTeam && (
                        <button className="btn-back-team" onClick={goBackToAll}>
                            <ArrowLeft size={16} />
                            All Teams
                        </button>
                    )}
                    <h1 className="page-title">
                        <Users size={22} />
                        {selectedTeam
                            ? selectedTeam.name
                            : (userRole === 'manager' ? 'All Teams' : 'My Team')}
                    </h1>
                    <p className="page-subtitle">
                        {selectedTeam
                            ? `${selectedTeam.member_count} member${selectedTeam.member_count !== 1 ? 's' : ''}`
                            : `${(data.performance || data.agents || []).length} agents`}
                    </p>
                </div>
            </div>

            {/* Team KPIs */}
            <div className="kpi-grid kpi-grid--3">
                <div className="kpi-card">
                    <div className="kpi-card-icon kpi-icon--blue"><Users size={20} /></div>
                    <div className="kpi-card-data">
                        <span className="kpi-card-value">{agents.length}</span>
                        <span className="kpi-card-label">Agents</span>
                    </div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-card-icon kpi-icon--green"><TrendingUp size={20} /></div>
                    <div className="kpi-card-data">
                        <span className="kpi-card-value">{teamAvg}<small>/100</small></span>
                        <span className="kpi-card-label">{selectedTeam ? 'Avg Score' : 'Team Avg Score'}</span>
                    </div>
                </div>
                <div className="kpi-card">
                    <div className="kpi-card-icon kpi-icon--amber"><Phone size={20} /></div>
                    <div className="kpi-card-data">
                        <span className="kpi-card-value">{teamTotalCalls}</span>
                        <span className="kpi-card-label">Total Calls</span>
                    </div>
                </div>
            </div>

            {/* Manager: Team overview cards (only show when no team is selected) */}
            {!selectedTeam && userRole === 'manager' && data.teams && data.teams.length > 0 && (
                <div className="teams-card-grid">
                    {data.teams.map(team => (
                        <div
                            key={team.id}
                            className="team-overview-card team-overview-card--clickable"
                            onClick={() => selectTeam(team)}
                        >
                            <div className="team-overview-icon"><Users size={18} /></div>
                            <div className="team-overview-info">
                                <h4>{team.name}</h4>
                                <span>{team.member_count} members</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Loading state for team detail */}
            {loadingTeam && (
                <div className="page-loading" style={{ height: 'auto', padding: '60px 0' }}>
                    <div className="loading-spinner" />
                    <p>Loading team data…</p>
                </div>
            )}

            {/* Agent Performance Table with Drill-Down */}
            {!loadingTeam && (
                <div className="dash-card">
                    <div className="dash-card-header">
                        <h3><BarChart3 size={16} /> {selectedTeam ? `${selectedTeam.name} — Agent Performance` : 'Agent Performance'}</h3>
                    </div>
                    <div className="dash-card-body" style={{ padding: 0 }}>
                        {agents.length === 0 ? (
                            <div className="team-empty-state">
                                {selectedTeam ? (
                                    <>
                                        <div className="team-empty-icon">
                                            <UserX size={36} />
                                        </div>
                                        <h4>No Activity for {selectedTeam.name}</h4>
                                        <p>
                                            {selectedTeam.member_count === 0
                                                ? 'No agents have been assigned to this team yet.'
                                                : 'No calls have been recorded for this team yet.'}
                                        </p>
                                        <div className="team-empty-stats">
                                            <div className="team-empty-stat">
                                                <span className="team-empty-stat-value">0</span>
                                                <span className="team-empty-stat-label">Agents</span>
                                            </div>
                                            <div className="team-empty-stat">
                                                <span className="team-empty-stat-value">0</span>
                                                <span className="team-empty-stat-label">Total Calls</span>
                                            </div>
                                            <div className="team-empty-stat">
                                                <span className="team-empty-stat-value">0</span>
                                                <span className="team-empty-stat-label">Avg Score</span>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <Users size={32} />
                                        <p>No agents found.</p>
                                    </>
                                )}
                            </div>
                        ) : (
                            <div className="agent-table">
                                {/* Header */}
                                <div className="agent-table-header">
                                    <span className="at-rank">#</span>
                                    <span className="at-name">Agent</span>
                                    {!selectedTeam && <span className="at-team">Team</span>}
                                    <span className="at-calls">Calls</span>
                                    <span className="at-score">Avg Score</span>
                                    <span className="at-perf">Performance</span>
                                    <span className="at-action"></span>
                                </div>

                                {/* Rows */}
                                {agents.map((agent, idx) => (
                                    <div key={agent.clerk_user_id}>
                                        <div
                                            className={`agent-table-row ${expandedAgent === agent.clerk_user_id ? 'expanded' : ''}`}
                                            onClick={() => toggleAgentDetail(agent.clerk_user_id)}
                                        >
                                            <span className="at-rank">{idx + 1}</span>
                                            <span className="at-name">
                                                <div className="agent-avatar">
                                                    <User size={14} />
                                                </div>
                                                {agent.name}
                                            </span>
                                            {!selectedTeam && <span className="at-team">{agent.team_id || '—'}</span>}
                                            <span className="at-calls">{agent.total_calls}</span>
                                            <span className="at-score" style={{
                                                color: getScoreColor(agent.avg_score),
                                                fontWeight: 700
                                            }}>
                                                {agent.avg_score}
                                            </span>
                                            <span className="at-perf">
                                                <div className="perf-bar-track">
                                                    <div
                                                        className="perf-bar-fill"
                                                        style={{
                                                            width: `${Math.min(agent.avg_score, 100)}%`,
                                                            background: getScoreColor(agent.avg_score),
                                                        }}
                                                    />
                                                </div>
                                            </span>
                                            <span className="at-action">
                                                {expandedAgent === agent.clerk_user_id
                                                    ? <ChevronUp size={16} />
                                                    : <ChevronDown size={16} />}
                                            </span>
                                        </div>

                                        {/* Agent Detail Panel */}
                                        <AnimatePresence>
                                            {expandedAgent === agent.clerk_user_id && (
                                                <motion.div
                                                    className="agent-detail-panel"
                                                    initial={{ height: 0, opacity: 0 }}
                                                    animate={{ height: 'auto', opacity: 1 }}
                                                    exit={{ height: 0, opacity: 0 }}
                                                    transition={{ duration: 0.25 }}
                                                >
                                                    {loadingAgent === agent.clerk_user_id ? (
                                                        <div className="agent-detail-loading">
                                                            <div className="loading-spinner small" />
                                                            <span>Loading call records…</span>
                                                        </div>
                                                    ) : (
                                                        <AgentDetailContent
                                                            agent={agent}
                                                            data={agentCalls[agent.clerk_user_id]}
                                                            navigate={navigate}
                                                            getScoreColor={getScoreColor}
                                                        />
                                                    )}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </motion.div>
    );
}

function AgentDetailContent({ agent, data, navigate, getScoreColor }) {
    const calls = data?.calls || [];
    const summary = data?.summary || {};

    return (
        <div className="agent-detail-inner">
            {/* Agent Stats */}
            <div className="agent-detail-stats">
                <div className="agent-detail-stat">
                    <span className="agent-detail-stat-value">{summary.total_calls || agent.total_calls || 0}</span>
                    <span className="agent-detail-stat-label">Total Calls</span>
                </div>
                <div className="agent-detail-stat">
                    <span className="agent-detail-stat-value" style={{ color: getScoreColor(summary.avg_score || agent.avg_score) }}>
                        {summary.avg_score || agent.avg_score || 0}
                    </span>
                    <span className="agent-detail-stat-label">Avg Score</span>
                </div>
                <div className="agent-detail-stat">
                    <span className="agent-detail-stat-value" style={{ color: '#34d399' }}>
                        {summary.max_score ?? '—'}
                    </span>
                    <span className="agent-detail-stat-label">Best</span>
                </div>
                <div className="agent-detail-stat">
                    <span className="agent-detail-stat-value" style={{ color: '#ef4444' }}>
                        {summary.min_score ?? '—'}
                    </span>
                    <span className="agent-detail-stat-label">Lowest</span>
                </div>
            </div>

            {/* Recent Calls */}
            <div className="agent-detail-calls">
                <h4>Recent Calls</h4>
                {calls.length === 0 ? (
                    <p className="agent-detail-empty">No call records found for this agent.</p>
                ) : (
                    <div className="agent-detail-calls-list">
                        {calls.map(call => (
                            <div
                                key={call.id}
                                className="agent-detail-call-row"
                                onClick={(e) => { e.stopPropagation(); navigate(`/history/${call.id}`); }}
                            >
                                <span className="adc-intent">{call.intent?.replace(/_/g, ' ') || 'Unknown'}</span>
                                <span className="adc-date">
                                    {call.start_time
                                        ? new Date(call.start_time).toLocaleDateString(undefined, {
                                            month: 'short', day: 'numeric'
                                        })
                                        : '—'}
                                </span>
                                <span className="adc-score" style={{ color: getScoreColor(call.overall_score) }}>
                                    {call.overall_score ?? '—'}
                                </span>
                                <span className="adc-grade">{call.grade || '—'}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
