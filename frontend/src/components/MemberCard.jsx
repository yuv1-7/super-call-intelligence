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

                    {/* Car-specific fields */}
                    {isCarPolicy && vehicleDisplay && (
                        <>
                            <div className="member-field">
                                <span className="label">Vehicle</span>
                                <span className="value">{vehicleDisplay}</span>
                            </div>
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

                    {/* Life-specific fields */}
                    {isLifePolicy && member.beneficiaries && (
                        <>
                            <div className="member-field">
                                <span className="label">Coverage</span>
                                <span className="value">${(member.coverageAmount || 0).toLocaleString()}</span>
                            </div>
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
                            <div className="member-field">
                                <span className="label">Room Rent</span>
                                <span className="value">{subLimits.roomRent || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">ICU</span>
                                <span className="value">{subLimits.icu || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Pre-Existing</span>
                                <span className="value">{member.preExistingWaiting || 'N/A'}</span>
                            </div>
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
            </div>
        </div>
    );
}
