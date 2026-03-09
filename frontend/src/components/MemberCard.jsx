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

    const isCarPolicy = member.policyId?.startsWith('CAR');
    const isLifePolicy = member.policyId?.startsWith('LIFE');
    const isMedicalPolicy = member.policyId?.startsWith('MED');

    const policyIcon = isMedicalPolicy ? '🏥' : isCarPolicy ? '🚗' : '🛡️';
    const policyBadgeClass = isMedicalPolicy ? 'medical' : isCarPolicy ? 'car' : 'life';

    return (
        <div className="card member">
            <div className="card-header">
                <div className="card-icon">👤</div>
                <div>
                    <div className="card-title">{member.name}</div>
                    <div className="card-subtitle">{member.policyId}</div>
                </div>
            </div>
            <div className="card-body">
                <div className="member-grid">
                    <div className="member-field">
                        <span className="label">Policy Type</span>
                        <span className="value">
                            <span className={`member-badge ${policyBadgeClass}`}>
                                {policyIcon} {member.coverageType}
                            </span>
                        </span>
                    </div>
                    <div className="member-field">
                        <span className="label">Status</span>
                        <span className="value">
                            <span className="member-badge active">{member.status}</span>
                        </span>
                    </div>
                    <div className="member-field">
                        <span className="label">Coverage Amount</span>
                        <span className="value">₹{(member.coverageAmount || 0).toLocaleString('en-IN')}</span>
                    </div>
                    <div className="member-field">
                        <span className="label">Premium</span>
                        <span className="value">₹{(member.premium || 0).toLocaleString('en-IN')}/yr</span>
                    </div>

                    {/* Car-specific fields */}
                    {isCarPolicy && member.vehicle && (
                        <>
                            <div className="member-field">
                                <span className="label">Vehicle</span>
                                <span className="value">{member.vehicle.year} {member.vehicle.make} {member.vehicle.model}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">License Plate</span>
                                <span className="value">{member.vehicle.licensePlate}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Deductible</span>
                                <span className="value">₹{(member.deductible || 0).toLocaleString('en-IN')}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Prior Claims</span>
                                <span className="value">{member.claimHistory?.length || 0}</span>
                            </div>
                        </>
                    )}

                    {/* Life-specific fields */}
                    {isLifePolicy && member.beneficiaries && (
                        <>
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
                        </>
                    )}

                    {/* Medical-specific fields */}
                    {isMedicalPolicy && (
                        <>
                            <div className="member-field">
                                <span className="label">Room Category</span>
                                <span className="value">{member.roomCategory || '—'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Copay</span>
                                <span className="value">{member.copay != null ? `${member.copay}%` : '—'}</span>
                            </div>
                            {member.deductible != null && (
                                <div className="member-field">
                                    <span className="label">Deductible</span>
                                    <span className="value">₹{member.deductible.toLocaleString('en-IN')}</span>
                                </div>
                            )}
                            <div className="member-field full-width">
                                <span className="label">Pre-Existing Status</span>
                                <span className="value">{member.preExistingWaiting || '—'}</span>
                            </div>
                            {member.networkHospitals?.length > 0 && (
                                <div className="member-field full-width">
                                    <span className="label">Network Hospitals</span>
                                    <span className="value">{member.networkHospitals.join(' • ')}</span>
                                </div>
                            )}
                            {member.subLimits && Object.keys(member.subLimits).length > 0 && (
                                <div className="member-field full-width">
                                    <span className="label">Sub-Limits</span>
                                    <span className="value">
                                        {Object.entries(member.subLimits).map(([k, v]) => `${k.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase()).trim()}: ${v}`).join(' • ')}
                                    </span>
                                </div>
                            )}
                            {member.coveredConditions?.length > 0 && (
                                <div className="member-field full-width">
                                    <span className="label">Covered Conditions</span>
                                    <span className="value">{member.coveredConditions.join(' • ')}</span>
                                </div>
                            )}
                            <div className="member-field">
                                <span className="label">Day-Care</span>
                                <span className="value">{member.dayCareProcedures ? 'Covered ✅' : 'Not Covered ❌'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Maternity</span>
                                <span className="value">{member.maternity ? 'Covered ✅' : 'Not Covered ❌'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Prior Claims</span>
                                <span className="value">{member.claimHistory?.length || 0}</span>
                            </div>
                        </>
                    )}

                    {/* Add-ons */}
                    {(isCarPolicy || isMedicalPolicy) && member.addOns?.length > 0 && (
                        <div className="member-field full-width">
                            <span className="label">Add-Ons</span>
                            <span className="value">{member.addOns.join(' • ')}</span>
                        </div>
                    )}

                    <div className="member-field">
                        <span className="label">Phone</span>
                        <span className="value">{member.phone}</span>
                    </div>
                    <div className="member-field">
                        <span className="label">Email</span>
                        <span className="value">{member.email}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
