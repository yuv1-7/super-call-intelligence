// pages/DevPage.jsx — Dev-only admin tools

import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi.js';
import { Settings, Trash2, Database, RefreshCw, AlertTriangle } from 'lucide-react';

const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

export default function DevPage() {
    const { fetchWithAuth } = useApi();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [actionResult, setActionResult] = useState(null);
    const [confirmAction, setConfirmAction] = useState(null);

    useEffect(() => {
        loadStats();
    }, []);

    async function loadStats() {
        setLoading(true);
        try {
            const res = await fetchWithAuth('/api/dev/stats');
            setStats(res.stats);
        } catch (err) {
            console.error('Failed to load stats:', err);
            setStats(null);
        } finally {
            setLoading(false);
        }
    }

    async function executeAction(action) {
        setConfirmAction(null);
        setActionResult(null);
        try {
            const res = await fetchWithAuth(`/api/dev/${action}`, { method: 'POST' });
            setActionResult({ success: true, message: res.message });
            loadStats();
        } catch (err) {
            setActionResult({ success: false, message: err.message });
        }
    }

    if (!DEV_MODE) {
        return (
            <div className="empty-state-large">
                <AlertTriangle size={48} />
                <h3>Dev Mode Disabled</h3>
                <p>Set VITE_DEV_MODE=true in frontend/.env to enable.</p>
            </div>
        );
    }

    return (
        <div className="dev-page">
            <h1><Settings size={24} /> Developer Tools</h1>
            <p className="dev-warning">
                <AlertTriangle size={16} />
                These actions directly modify the database. Use with caution.
            </p>

            {/* DB Stats */}
            <div className="dashboard-card">
                <div className="card-header-row">
                    <h3><Database size={18} /> Database Stats</h3>
                    <button className="btn-link" onClick={loadStats}>
                        <RefreshCw size={14} /> Refresh
                    </button>
                </div>
                {loading ? (
                    <div className="dashboard-loading"><div className="loading-spinner" /></div>
                ) : stats ? (
                    <div className="stats-grid compact">
                        {Object.entries(stats).map(([table, count]) => (
                            <div key={table} className="stat-card small">
                                <span className="stat-value">{count}</span>
                                <span className="stat-label">{table}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="empty-state">Could not load DB stats. Is the server running?</p>
                )}
            </div>

            {/* Actions */}
            <div className="dashboard-card">
                <h3>Destructive Actions</h3>
                <div className="dev-actions">
                    <div className="dev-action-row">
                        <div>
                            <strong>Clear Call History</strong>
                            <p>Deletes all call records and their associated evaluations.</p>
                        </div>
                        <button
                            className="btn-danger"
                            onClick={() => setConfirmAction('clear-history')}
                        >
                            <Trash2 size={14} /> Clear
                        </button>
                    </div>
                    <div className="dev-action-row">
                        <div>
                            <strong>Clear Evaluations Only</strong>
                            <p>Deletes all evaluations but keeps call records.</p>
                        </div>
                        <button
                            className="btn-danger"
                            onClick={() => setConfirmAction('clear-evaluations')}
                        >
                            <Trash2 size={14} /> Clear
                        </button>
                    </div>
                </div>
            </div>

            {/* Confirm Modal */}
            {confirmAction && (
                <div className="modal-overlay" onClick={() => setConfirmAction(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3><AlertTriangle size={20} /> Confirm Action</h3>
                        <p>Are you sure you want to <strong>{confirmAction}</strong>? This cannot be undone.</p>
                        <div className="modal-actions">
                            <button className="btn-secondary" onClick={() => setConfirmAction(null)}>Cancel</button>
                            <button className="btn-danger" onClick={() => executeAction(confirmAction)}>
                                Yes, proceed
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Action Result */}
            {actionResult && (
                <div className={`action-result ${actionResult.success ? 'success' : 'error'}`}>
                    {actionResult.message}
                </div>
            )}
        </div>
    );
}
