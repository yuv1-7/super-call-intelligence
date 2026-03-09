/**
 * FNOL Form Card — Pre-filled First Notice of Loss form
 * Shows after call ends alongside the evaluation scorecard.
 * Renders claim-type-specific fields (car vs life) from accumulated call data.
 */
import { useRef } from 'react';

export default function FNOLFormCard({ fnolData }) {
    const formRef = useRef(null);

    if (!fnolData) return null;

    const { facts = {}, member, intent } = fnolData;

    const isCarClaim = intent?.startsWith('car_') || member?.policyId?.startsWith('CAR');
    const isLifeClaim = intent?.startsWith('life_') || member?.policyId?.startsWith('LIFE');

    // Generate a mock claim reference number
    const claimRef = isCarClaim
        ? `CLM-A-${Date.now().toString().slice(-6)}`
        : `CLM-L-${Date.now().toString().slice(-6)}`;

    const today = new Date().toLocaleDateString('en-IN', {
        year: 'numeric', month: 'long', day: 'numeric',
    });

    const handleExportPDF = async () => {
        const element = formRef.current;
        if (!element) return;

        // Temporarily switch to export (white) mode for the PDF capture
        element.classList.add('export-mode');

        const html2pdf = (await import('html2pdf.js')).default;

        const opt = {
            margin: [0.4, 0.5, 0.4, 0.5],
            filename: `FNOL_${member?.policyId || 'Unknown'}_${claimRef}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
            jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' },
        };

        // html2pdf returns a promise-like chain
        await html2pdf().set(opt).from(element).save();

        // Restore dark theme
        element.classList.remove('export-mode');
    };

    const formatCurrency = (val) => val != null ? `₹${val.toLocaleString('en-IN')}` : '—';

    // Render a single form field row
    const Field = ({ label, value, fullWidth }) => (
        <div className={`fnol-field${fullWidth ? ' full-width' : ''}`}>
            <label className="fnol-label">{label}</label>
            <div className="fnol-value">{value || '—'}</div>
        </div>
    );

    // Boolean field display
    const BoolField = ({ label, value }) => (
        <div className="fnol-field">
            <label className="fnol-label">{label}</label>
            <div className="fnol-value">
                {value === true ? '✅ Yes' : value === false ? '❌ No' : '—'}
            </div>
        </div>
    );

    return (
        <div className="fnol-form-wrapper">
            {/* Export Button */}
            <div className="fnol-actions">
                <button className="fnol-export-btn" onClick={handleExportPDF}>
                    📄 Export as PDF
                </button>
            </div>

            {/* The printable form */}
            <div className="fnol-form" ref={formRef}>
                {/* ─── Form Header ─── */}
                <div className="fnol-header">
                    <div className="fnol-header-left">
                        <h2 className="fnol-title">First Notice of Loss</h2>
                        <p className="fnol-subtitle">
                            {isCarClaim ? 'Automobile Insurance Claim Report' : 'Life Insurance Death Claim Report'}
                        </p>
                    </div>
                    <div className="fnol-header-right">
                        <div className="fnol-header-meta">
                            <span className="fnol-meta-label">Claim Ref.</span>
                            <span className="fnol-meta-value mono">{claimRef}</span>
                        </div>
                        <div className="fnol-header-meta">
                            <span className="fnol-meta-label">Report Date</span>
                            <span className="fnol-meta-value">{today}</span>
                        </div>
                        <span className={`fnol-type-badge ${isCarClaim ? 'car' : 'life'}`}>
                            {isCarClaim ? '🚗 Auto' : '🛡️ Life'}
                        </span>
                    </div>
                </div>

                {/* ─── Section 1: Policyholder Information ─── */}
                <div className="fnol-section">
                    <h3 className="fnol-section-title">
                        <span className="fnol-section-num">01</span>
                        Policyholder Information
                    </h3>
                    <div className="fnol-grid">
                        <Field label="Full Name" value={member?.name} />
                        <Field label="Policy Number" value={member?.policyId || facts.policy_number} />
                        <Field label="Phone" value={member?.phone} />
                        <Field label="Email" value={member?.email} />
                        <Field label="Policy Type" value={member?.policyType} />
                        <Field label="Coverage Type" value={member?.coverageType} />
                        <Field label="Policy Status" value={member?.status} />
                        <Field label="Policy Period" value={
                            member?.startDate && member?.endDate
                                ? `${member.startDate} to ${member.endDate}`
                                : null
                        } />
                    </div>
                </div>

                {/* ─── Section 2: Caller / Claimant Information ─── */}
                <div className="fnol-section">
                    <h3 className="fnol-section-title">
                        <span className="fnol-section-num">02</span>
                        Caller / Claimant Information
                    </h3>
                    <div className="fnol-grid">
                        <Field label="Caller Name" value={facts.caller_name} />
                        {isLifeClaim && (
                            <Field label="Relationship to Policyholder" value={facts.relationship_to_policyholder} />
                        )}
                    </div>
                </div>

                {/* ─── Section 3: Incident / Loss Details ─── */}
                <div className="fnol-section">
                    <h3 className="fnol-section-title">
                        <span className="fnol-section-num">03</span>
                        {isLifeClaim ? 'Death Claim Details' : 'Incident / Loss Details'}
                    </h3>
                    <div className="fnol-grid">
                        <Field label={isLifeClaim ? 'Date of Death' : 'Date of Incident'} value={facts.date_of_incident} />
                        {isCarClaim && <Field label="Time of Incident" value={facts.time_of_incident} />}
                        <Field label={isLifeClaim ? 'Location of Death' : 'Location of Incident'} value={facts.location_of_incident} />
                        {isLifeClaim && <Field label="Cause of Death" value={facts.cause_of_death} />}
                        {isCarClaim && (
                            <Field label="Incident Description" value={facts.incident_description} fullWidth />
                        )}
                    </div>
                </div>

                {/* ─── Section 4 (Car): Vehicle & Accident Details ─── */}
                {isCarClaim && (
                    <div className="fnol-section">
                        <h3 className="fnol-section-title">
                            <span className="fnol-section-num">04</span>
                            Vehicle & Accident Details
                        </h3>
                        <div className="fnol-grid">
                            <Field label="Vehicle" value={
                                member?.vehicle
                                    ? `${member.vehicle.year} ${member.vehicle.make} ${member.vehicle.model}`
                                    : null
                            } />
                            <Field label="Color" value={member?.vehicle?.color} />
                            <Field label="VIN" value={member?.vehicle?.vin} />
                            <Field label="License Plate" value={member?.vehicle?.licensePlate} />
                            <BoolField label="Vehicle Drivable" value={facts.vehicle_drivable} />
                            <BoolField label="Police Report Filed" value={facts.police_report_filed} />
                            <Field label="Police Report Number" value={facts.police_report_number} />
                            <Field label="Injuries Reported" value={facts.injuries_reported} />
                            <Field label="Other Parties Involved" value={facts.other_parties_involved} />
                        </div>
                    </div>
                )}

                {/* ─── Section 4 (Life): Beneficiary Information ─── */}
                {isLifeClaim && member?.beneficiaries && (
                    <div className="fnol-section">
                        <h3 className="fnol-section-title">
                            <span className="fnol-section-num">04</span>
                            Beneficiary Information
                        </h3>
                        <div className="fnol-beneficiaries">
                            <div className="fnol-table-header">
                                <span>Name</span>
                                <span>Relationship</span>
                                <span>Share</span>
                            </div>
                            {member.beneficiaries.map((b, i) => (
                                <div key={i} className="fnol-table-row">
                                    <span>{b.name}</span>
                                    <span>{b.relationship}</span>
                                    <span>{b.share}</span>
                                </div>
                            ))}
                        </div>
                        <div className="fnol-grid" style={{ marginTop: '12px' }}>
                            <Field label="Contestability Status" value={
                                member.contestabilityExpired ? 'Expired — No additional review required' : 'Active — Within 2-year contestability period'
                            } />
                        </div>
                    </div>
                )}

                {/* ─── Section 5: Coverage & Financial Details ─── */}
                <div className="fnol-section">
                    <h3 className="fnol-section-title">
                        <span className="fnol-section-num">{isCarClaim ? '05' : '05'}</span>
                        Coverage & Financial Details
                    </h3>
                    <div className="fnol-grid">
                        <Field label="Coverage Amount" value={formatCurrency(member?.coverageAmount)} />
                        <Field label="Annual Premium" value={formatCurrency(member?.premium)} />
                        {isCarClaim && <Field label="Deductible" value={formatCurrency(member?.deductible)} />}
                        {isCarClaim && member?.addOns?.length > 0 && (
                            <Field label="Active Add-Ons" value={member.addOns.join(' • ')} fullWidth />
                        )}
                        {isLifeClaim && member?.cashValue != null && (
                            <Field label="Cash Value" value={formatCurrency(member.cashValue)} />
                        )}
                        {isCarClaim && member?.claimHistory?.length > 0 && (
                            <Field label="Prior Claims" value={`${member.claimHistory.length} on file`} />
                        )}
                    </div>
                </div>

                {/* ─── Footer ─── */}
                <div className="fnol-footer">
                    <div className="fnol-footer-left">
                        <p>This form was auto-generated by CallIQ based on details captured during the FNOL call.</p>
                        <p>All information is subject to verification. A claims adjuster will review this report.</p>
                    </div>
                    <div className="fnol-footer-right">
                        <div className="fnol-signature-box">
                            <div className="fnol-signature-line"></div>
                            <span>Agent Signature</span>
                        </div>
                        <div className="fnol-signature-box">
                            <div className="fnol-signature-line"></div>
                            <span>Date</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
