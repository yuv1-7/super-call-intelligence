// pages/TeamDashboardPage.jsx — Team overview for leads and managers

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import { Users, TrendingUp, Award, BarChart3 } from 'lucide-react';

export default function TeamDashboardPage({ userRole }) {
    const navigate = useNavigate();
    const { fetchWithAuth } = useApi();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

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

    function getScoreColor(score) {
        if (score >= 75) return '#10b981';
        if (score >= 60) return '#f59e0b';
        return '#ef4444';
    }

    if (loading) {
        return <div className="dashboard-loading"><div className="loading-spinner" /><p>Loading team data...</p></div>;
    }

    if (!data) {
        return <div className="empty-state-large"><h3>Unable to load team data</h3></div>;
    }

    const agents = data.performance || data.agents || [];

    return (
        <div className="team-page">
            <h1>
                <Users size={24} />
                {userRole === 'manager' ? 'All Teams' : 'My Team'}
            </h1>

            {/* Manager: Team overview cards */}
            {userRole === 'manager' && data.teams && (
                <div className="teams-grid">
                    {data.teams.map(team => (
                        <div key={team.id} className="team-overview-card">
                            <h3>{team.name}</h3>
                            <div className="team-stat">
                                <Users size={16} />
                                <span>{team.member_count} members</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Agent performance table */}
            <div className="dashboard-card">
                <h3><BarChart3 size={18} /> Agent Performance</h3>
                {agents.length === 0 ? (
                    <p className="empty-state">No agents found.</p>
                ) : (
                    <div className="team-table full">
                        <div className="team-row header">
                            <span>Agent</span>
                            <span>Team</span>
                            <span>Total Calls</span>
                            <span>Avg Score</span>
                            <span>Performance</span>
                        </div>
                        {agents.map(agent => (
                            <div key={agent.clerk_user_id} className="team-row">
                                <span className="agent-name">{agent.name}</span>
                                <span>{agent.team_id || '—'}</span>
                                <span>{agent.total_calls}</span>
                                <span style={{ color: getScoreColor(agent.avg_score), fontWeight: 600 }}>
                                    {agent.avg_score}
                                </span>
                                <span>
                                    <div className="mini-bar-track">
                                        <div
                                            className="mini-bar-fill"
                                            style={{
                                                width: `${agent.avg_score}%`,
                                                backgroundColor: getScoreColor(agent.avg_score),
                                            }}
                                        />
                                    </div>
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
