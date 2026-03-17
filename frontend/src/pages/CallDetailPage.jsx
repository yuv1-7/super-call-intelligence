// pages/CallDetailPage.jsx — Full call detail with evaluation

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi.js';
import PostCallCard from '../components/PostCallCard.jsx';
import FNOLFormCard from '../components/FNOLFormCard.jsx';
import { ArrowLeft } from 'lucide-react';

export default function CallDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { fetchWithAuth } = useApi();
    const [call, setCall] = useState(null);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState(0);

    useEffect(() => {
        loadCall();
    }, [id]);

    async function loadCall() {
        setLoading(true);
        try {
            const data = await fetchWithAuth(`/api/calls/${id}`);
            setCall(data);
        } catch (err) {
            console.error('Failed to load call:', err);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="dashboard-loading">
                <div className="loading-spinner" />
                <p>Loading call details...</p>
            </div>
        );
    }

    if (!call) {
        return (
            <div className="empty-state-large">
                <h3>Call not found</h3>
                <button className="btn-link" onClick={() => navigate('/history')}>Back to history</button>
            </div>
        );
    }

    const evaluation = call.evaluation;

    return (
        <div className="call-detail-page">
            <button className="btn-back" onClick={() => navigate('/history')}>
                <ArrowLeft size={16} /> Back to History
            </button>

            <div className="call-detail-header">
                <div>
                    <h1>Call #{call.id}</h1>
                    <p className="call-detail-meta">
                        {call.start_time ? new Date(call.start_time).toLocaleString() : '—'}
                        {' • '}
                        {call.intent?.replace(/_/g, ' ') || 'Unknown'}
                        {call.agent_name && ` • ${call.agent_name}`}
                        {call.policy_id && ` • ${call.policy_id}`}
                    </p>
                </div>
                {evaluation && (
                    <div className="call-detail-score" style={{
                        color: evaluation.overall_score >= 75 ? '#10b981' :
                               evaluation.overall_score >= 60 ? '#f59e0b' : '#ef4444'
                    }}>
                        <span className="score-number">{evaluation.overall_score}</span>
                        <span className="score-grade">{evaluation.grade}</span>
                    </div>
                )}
            </div>

            {evaluation ? (
                <>
                    <div className="post-call-tabs">
                        <button
                            className={`post-call-tab${tab === 0 ? ' active' : ''}`}
                            onClick={() => setTab(0)}
                        >
                            📊 Call Analytics
                        </button>
                        <button
                            className={`post-call-tab${tab === 1 ? ' active' : ''}`}
                            onClick={() => setTab(1)}
                        >
                            📋 FNOL Report
                        </button>
                        <button
                            className={`post-call-tab${tab === 2 ? ' active' : ''}`}
                            onClick={() => setTab(2)}
                        >
                            🎙️ Transcript
                        </button>
                    </div>
                    <div className="post-call-tab-content">
                        {tab === 0 && <PostCallCard evaluation={evaluation} />}
                        {tab === 1 && <FNOLFormCard fnolData={{
                            facts: call.accumulated_facts,
                            member: call.member_snapshot,
                            intent: call.intent,
                        }} />}
                        {tab === 2 && (
                            <div className="transcript-review">
                                {(call.transcript || []).map((line, i) => (
                                    <div key={i} className={`transcript-line ${line.speaker?.toLowerCase()}`}>
                                        <span className="transcript-speaker">{line.speaker}</span>
                                        <span className="transcript-time">{line.timestamp}</span>
                                        <p className="transcript-text">{line.text}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </>
            ) : (
                <div className="empty-state-large">
                    <h3>No evaluation available</h3>
                    <p>This call does not have a post-call evaluation.</p>
                </div>
            )}
        </div>
    );
}
