export default function MemberCard({ member }) {
    if (!member) {
        return (
            <div className="card member compact-empty">
                <div className="card-header">
                    <div className="card-icon">👤</div>
                    <div>
                        <div className="card-title">Policyholder Profile</div>
                        <div className="card-subtitle">Waiting for policy ID...</div>
                    </div>
                </div>
            </div>
        );
    }

    // Determine policy type from policyId prefix (CAR-, LIFE-, MED-)
    const policyId = member.policyId || '';
    const isLifePolicy = policyId.toUpperCase().startsWith('LIFE');
    const isMedicalPolicy = policyId.toUpperCase().startsWith('MED');
    const isCarPolicy = policyId.toUpperCase().startsWith('CAR');

    // Vehicle is a nested object { make, model, year, color, vin, licensePlate }
    const vehicle = member.vehicle || {};
    const vehicleDisplay = vehicle.make
        ? `${vehicle.year} ${vehicle.make} ${vehicle.model}`
        : null;

    // Add-ons (camelCase from backend)
    const addOns = member.addOns || [];

    // Medical sub-limits (nested object)
    const subLimits = member.subLimits || {};

    // Medical-specific arrays
    const networkHospitals = member.networkHospitals || [];
    const coveredConditions = member.coveredConditions || [];

    // Claim history
    const claimHistory = member.claimHistory || [];

    // Policy date helpers
    const isNearExpiry = () => {
        if (!member.endDate || member.endDate === 'Lifetime') return false;
        const end = new Date(member.endDate);
        const now = new Date();
        const daysLeft = Math.round((end - now) / (1000 * 60 * 60 * 24));
        return daysLeft >= 0 && daysLeft <= 90;
    };

    return (
        <div className="card member">
            <div className="card-header">
                <div className="card-icon">👤</div>
                <div>
                    <div className="card-title">{member.name}</div>
                    <div className="card-subtitle">{policyId}</div>
                </div>
            </div>
            <div className="card-body">
                <div className="member-grid">
                    <div className="member-field">
                        <span className="label">Status</span>
                        <span className="value">
                            <span className={`member-badge ${member.status === 'Active' ? 'active' : ''}`}>
                                {member.status || 'Unknown'}
                            </span>
                        </span>
                    </div>
                    <div className="member-field">
                        <span className="label">Age</span>
                        <span className="value">{member.age || 'N/A'}</span>
                    </div>

                    {/* Policy type & coverage — all policy types */}
                    {member.policyType && (
                        <div className="member-field full-width">
                            <span className="label">Plan</span>
                            <span className="value">{member.policyType}</span>
                        </div>
                    )}

                    {/* Policy dates */}
                    {member.startDate && (
                        <div className="member-field">
                            <span className="label">Effective</span>
                            <span className="value">{member.startDate}</span>
                        </div>
                    )}
                    {member.endDate && (
                        <div className="member-field">
                            <span className="label">Expires</span>
                            <span className="value">
                                {member.endDate}
                                {isNearExpiry() && <span className="member-badge" style={{ marginLeft: 6, background: 'rgba(249,115,22,0.15)', color: '#f97316', fontSize: '0.65rem' }}>⚠️ Near Expiry</span>}
                            </span>
                        </div>
                    )}

                    {/* Premium */}
                    {member.premium != null && (
                        <div className="member-field">
                            <span className="label">Premium</span>
                            <span className="value">${member.premium.toLocaleString()}/yr</span>
                        </div>
                    )}

                    {/* ─── Car-specific fields ─── */}
                    {isCarPolicy && vehicleDisplay && (
                        <>
                            <div className="member-field">
                                <span className="label">Vehicle</span>
                                <span className="value">{vehicleDisplay}</span>
                            </div>
                            {vehicle.color && (
                                <div className="member-field">
                                    <span className="label">Color</span>
                                    <span className="value">{vehicle.color}</span>
                                </div>
                            )}
                            <div className="member-field">
                                <span className="label">VIN</span>
                                <span className="value">{vehicle.vin || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">License Plate</span>
                                <span className="value">{vehicle.licensePlate || 'N/A'}</span>
                            </div>
                        </>
                    )}

                    {/* Car coverage details */}
                    {isCarPolicy && (
                        <>
                            <div className="member-field">
                                <span className="label">Coverage</span>
                                <span className="value">${(member.coverageAmount || 0).toLocaleString()}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Deductible</span>
                                <span className="value">${(member.deductible || 0).toLocaleString()}</span>
                            </div>
                        </>
                    )}

                    {/* Add-ons (car and medical) */}
                    {addOns.length > 0 && (
                        <div className="member-field full-width">
                            <span className="label">Add-Ons</span>
                            <span className="value">{addOns.join(' • ')}</span>
                        </div>
                    )}

                    {/* ─── Life-specific fields ─── */}
                    {isLifePolicy && member.beneficiaries && (
                        <>
                            <div className="member-field">
                                <span className="label">Coverage</span>
                                <span className="value">${(member.coverageAmount || 0).toLocaleString()}</span>
                            </div>
                            {member.cashValue != null && (
                                <div className="member-field">
                                    <span className="label">Cash Value</span>
                                    <span className="value">${member.cashValue.toLocaleString()}</span>
                                </div>
                            )}
                            <div className="member-field full-width">
                                <span className="label">Beneficiaries</span>
                                <span className="value">
                                    {member.beneficiaries.map((b) => `${b.name} (${b.relationship} — ${b.share})`).join(', ')}
                                </span>
                            </div>
                            <div className="member-field">
                                <span className="label">Contestability</span>
                                <span className="value">{member.contestabilityExpired ? 'Expired ✅' : 'Active ⚠️'}</span>
                            </div>
                            {member.medicalHistory && (
                                <div className="member-field full-width">
                                    <span className="label">Medical History</span>
                                    <span className="value">{member.medicalHistory}</span>
                                </div>
                            )}
                            {member.lastPremiumPaid && (
                                <div className="member-field">
                                    <span className="label">Last Premium Paid</span>
                                    <span className="value">{member.lastPremiumPaid}</span>
                                </div>
                            )}
                        </>
                    )}

                    {/* ─── Medical-specific fields ─── */}
                    {isMedicalPolicy && (
                        <>
                            <div className="member-field">
                                <span className="label">Coverage</span>
                                <span className="value">${(member.coverageAmount || 0).toLocaleString()}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Copay</span>
                                <span className="value">{member.copay != null ? `${member.copay}%` : 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Deductible</span>
                                <span className="value">${(member.deductible || 0).toLocaleString()}</span>
                            </div>
                            {member.roomCategory && (
                                <div className="member-field">
                                    <span className="label">Room Category</span>
                                    <span className="value">{member.roomCategory}</span>
                                </div>
                            )}
                            <div className="member-field">
                                <span className="label">Room Rent</span>
                                <span className="value">{subLimits.roomRent || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">ICU</span>
                                <span className="value">{subLimits.icu || 'N/A'}</span>
                            </div>
                            {subLimits.ambulance && (
                                <div className="member-field">
                                    <span className="label">Ambulance</span>
                                    <span className="value">{subLimits.ambulance}</span>
                                </div>
                            )}
                            <div className="member-field">
                                <span className="label">Pre-Existing</span>
                                <span className="value">{member.preExistingWaiting || 'N/A'}</span>
                            </div>
                            {member.maternity != null && (
                                <div className="member-field">
                                    <span className="label">Maternity</span>
                                    <span className="value">{member.maternity ? 'Covered ✅' : 'Not Covered'}</span>
                                </div>
                            )}
                            {member.dayCareProcedures != null && (
                                <div className="member-field">
                                    <span className="label">Day-Care</span>
                                    <span className="value">{member.dayCareProcedures ? 'Covered ✅' : 'Not Covered'}</span>
                                </div>
                            )}
                            {networkHospitals.length > 0 && (
                                <div className="member-field full-width">
                                    <span className="label">Network Hospitals</span>
                                    <span className="value">{networkHospitals.join(' • ')}</span>
                                </div>
                            )}
                            {coveredConditions.length > 0 && (
                                <div className="member-field full-width">
                                    <span className="label">Covered Conditions</span>
                                    <span className="value">{coveredConditions.join(' • ')}</span>
                                </div>
                            )}
                        </>
                    )}

                    <div className="member-field">
                        <span className="label">Phone</span>
                        <span className="value">{member.phone || 'N/A'}</span>
                    </div>
                    <div className="member-field">
                        <span className="label">Email</span>
                        <span className="value">{member.email || 'N/A'}</span>
                    </div>
                </div>

                {/* ─── Claim History ─── */}
                {claimHistory.length > 0 && (
                    <div className="member-claims">
                        <div className="member-claims-header">📂 Prior Claims ({claimHistory.length})</div>
                        <div className="member-claims-list">
                            {claimHistory.map((claim, i) => (
                                <div key={i} className="member-claim-row">
                                    <div className="member-claim-info">
                                        <span className="member-claim-id">{claim.claimId}</span>
                                        <span className="member-claim-type">{claim.type}</span>
                                    </div>
                                    <div className="member-claim-meta">
                                        <span className="member-claim-date">{claim.date}</span>
                                        <span className="member-claim-amount">${claim.amount?.toLocaleString()}</span>
                                        <span className={`member-badge ${claim.status === 'Settled' ? 'active' : 'pending'}`}>
                                            {claim.status}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
