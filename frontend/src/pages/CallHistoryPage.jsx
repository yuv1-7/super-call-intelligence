// pages/CallHistoryPage.jsx — Paginated call history with evaluation detail

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import { Search, Filter, ChevronLeft, ChevronRight, Clock, Award, Trash2 } from 'lucide-react';

export default function CallHistoryPage({ userRole }) {
    const navigate = useNavigate();
    const { fetchWithAuth } = useApi();
    const [calls, setCalls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [offset, setOffset] = useState(0);
    const [filterType, setFilterType] = useState('all');
    const [deletingId, setDeletingId] = useState(null);
    const limit = 20;

    useEffect(() => {
        loadCalls();
    }, [offset, filterType]);

    async function loadCalls() {
        setLoading(true);
        try {
            let url = `/api/calls?limit=${limit}&offset=${offset}`;
            if (filterType !== 'all') {
                url += `&claim_type=${encodeURIComponent(filterType)}`;
            }
            const res = await fetchWithAuth(url);
            setCalls(res.calls || []);
        } catch (err) {
            console.error('Failed to load calls:', err);
        } finally {
            setLoading(false);
        }
    }

    function formatDuration(secs) {
        if (!secs) return '—';
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function getScoreColor(score) {
        if (score >= 75) return '#10b981';
        if (score >= 60) return '#f59e0b';
        return '#ef4444';
    }

    async function handleDelete(e, callId) {
        e.stopPropagation();
        if (!window.confirm('Delete this call log? This cannot be undone.')) return;
        setDeletingId(callId);
        try {
            await fetchWithAuth(`/api/calls/${callId}`, { method: 'DELETE' });
            setCalls(prev => prev.filter(c => c.id !== callId));
        } catch (err) {
            console.error('Failed to delete call:', err);
            alert('Failed to delete call. Please try again.');
        } finally {
            setDeletingId(null);
        }
    }

    return (
        <div className="history-page">
            <div className="history-header">
                <h1>Call History</h1>
                <div className="history-filters">
                    <select
                        className="filter-select"
                        value={filterType}
                        onChange={e => { setFilterType(e.target.value); setOffset(0); }}
                    >
                        <option value="all">All Types</option>
                        <option value="car_insurance">Car Insurance</option>
                        <option value="life_insurance">Life Insurance</option>
                        <option value="medical_insurance">Medical Insurance</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="dashboard-loading">
                    <div className="loading-spinner" />
                    <p>Loading call history...</p>
                </div>
            ) : calls.length === 0 ? (
                <div className="empty-state-large">
                    <Clock size={48} />
                    <h3>No calls found</h3>
                    <p>Start making calls to see your history here.</p>
                </div>
            ) : (
                <>
                    <div className="calls-table">
                        <div className={`calls-row header ${userRole !== 'agent' ? 'with-agent' : ''}`}>
                            <span>Date</span>
                            <span>Intent</span>
                            {userRole !== 'agent' && <span>Agent</span>}
                            <span>Duration</span>
                            <span>Policy</span>
                            <span>Score</span>
                            <span>Grade</span>
                            <span></span>
                        </div>
                        {calls.map(call => (
                            <div
                                key={call.id}
                                className={`calls-row clickable ${userRole !== 'agent' ? 'with-agent' : ''}`}
                                onClick={() => navigate(`/history/${call.id}`)}
                            >
                                <span className="call-date">
                                    {call.start_time ? new Date(call.start_time).toLocaleString(undefined, {
                                        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                    }) : '—'}
                                </span>
                                <span className="call-intent-badge">
                                    {call.intent?.replace(/_/g, ' ') || 'Unknown'}
                                </span>
                                {userRole !== 'agent' && (
                                    <span className="call-agent-name">{call.agent_name || '—'}</span>
                                )}
                                <span>{formatDuration(call.duration_secs)}</span>
                                <span className="call-policy">{call.policy_id || '—'}</span>
                                <span className="call-score" style={{ color: getScoreColor(call.overall_score) }}>
                                    {call.overall_score ?? '—'}
                                </span>
                                <span className="call-grade" style={{ color: getScoreColor(call.overall_score) }}>
                                    {call.grade || '—'}
                                </span>
                                <span className="call-delete-col" onClick={e => e.stopPropagation()}>
                                    <button
                                        className="btn-delete-call"
                                        onClick={e => handleDelete(e, call.id)}
                                        disabled={deletingId === call.id}
                                        title="Delete call"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </span>
                            </div>
                        ))}
                    </div>

                    {/* Pagination */}
                    <div className="pagination">
                        <button
                            className="btn-page"
                            disabled={offset === 0}
                            onClick={() => setOffset(Math.max(0, offset - limit))}
                        >
                            <ChevronLeft size={16} /> Previous
                        </button>
                        <span className="page-info">
                            Showing {offset + 1}–{offset + calls.length}
                        </span>
                        <button
                            className="btn-page"
                            disabled={calls.length < limit}
                            onClick={() => setOffset(offset + limit)}
                        >
                            Next <ChevronRight size={16} />
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}
