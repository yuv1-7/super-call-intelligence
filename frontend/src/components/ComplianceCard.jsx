export default function ComplianceCard({ alerts }) {
    if (!alerts || alerts.length === 0) {
        return (
            <div className="card compliance compact-empty">
                <div className="card-header">
                    <div className="card-icon">⚖️</div>
                    <div>
                        <div className="card-title">Compliance Alerts</div>
                        <div className="card-subtitle">No active alerts</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="card compliance">
            <div className="card-header">
                <div className="card-icon">⚖️</div>
                <div>
                    <div className="card-title">Compliance Alerts</div>
                    <div className="card-subtitle">{alerts.length} active alert{alerts.length !== 1 ? 's' : ''}</div>
                </div>
            </div>
            <div className="card-body">
                {alerts.map((alert, idx) => {
                    const sev = (alert.severity || 'medium').toLowerCase();
                    return (
                    <div key={alert.document_id || alert.ruleId || idx} className={`compliance-alert ${sev}`}>
                        <div className="alert-title">
                            {sev === 'critical' ? '🚨' : sev === 'high' ? '⚠️' : '📋'}{' '}
                            {alert.title}
                        </div>
                        {alert.content || alert.message}
                    </div>
                    );
                })}
            </div>
        </div>
    );
}
