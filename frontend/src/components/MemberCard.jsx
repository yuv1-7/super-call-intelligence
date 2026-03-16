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

    // Determine policy type from policy_number prefix
    const policyNumber = member.policy_number || '';
    const isLifePolicy = policyNumber.toUpperCase().startsWith('LIFE');
    const isMedicalPolicy = policyNumber.toUpperCase().startsWith('MED');
    const isCarPolicy = policyNumber.toUpperCase().startsWith('CAR');

    // Coverage limits (car)
    const limits = member.coverage_limits || {};
    const collisionDeductible = limits.collision_deductible || 'N/A';
    const comprehensiveDeductible = limits.comprehensive_deductible || 'N/A';
    const bodilyInjury = limits.bodily_injury || 'N/A';
    const propertyDamage = limits.property_damage || 'N/A';

    // Add-ons
    const addOns = member.add_ons || [];

    // Medical-specific fields
    const networkHospitals = member.networkHospitals || [];
    const coveredConditions = member.coveredConditions || [];

    return (
        <div className="card member">
            <div className="card-header">
                <div className="card-icon">👤</div>
                <div>
                    <div className="card-title">{member.name}</div>
                    <div className="card-subtitle">{policyNumber}</div>
                </div>
            </div>
            <div className="card-body">
                <div className="member-grid">
                    <div className="member-field">
                        <span className="label">Status</span>
                        <span className="value">
                            <span className={`member-badge ${member.policy_status === 'ACTIVE' ? 'active' : ''}`}>
                                {member.policy_status || 'Unknown'}
                            </span>
                        </span>
                    </div>
                    <div className="member-field">
                        <span className="label">DOB</span>
                        <span className="value">{member.dob || 'N/A'}</span>
                    </div>

                    {/* Car-specific fields */}
                    {isCarPolicy && member.vehicle && (
                        <>
                            <div className="member-field">
                                <span className="label">Vehicle</span>
                                <span className="value">{member.vehicle}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">VIN</span>
                                <span className="value">{member.vin || 'N/A'}</span>
                            </div>
                        </>
                    )}

                    {/* Car coverage limits */}
                    {isCarPolicy && (
                        <>
                            <div className="member-field">
                                <span className="label">Bodily Injury</span>
                                <span className="value">{bodilyInjury}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Property Damage</span>
                                <span className="value">{propertyDamage}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Collision Deductible</span>
                                <span className="value">{collisionDeductible}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Comp. Deductible</span>
                                <span className="value">{comprehensiveDeductible}</span>
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
                                <span className="label">Sum Insured</span>
                                <span className="value">{member.sumInsured || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Copay</span>
                                <span className="value">{member.copayPercentage || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">Room Rent Cap</span>
                                <span className="value">{member.roomRentCap || 'N/A'}</span>
                            </div>
                            <div className="member-field">
                                <span className="label">ICU Cap</span>
                                <span className="value">{member.icuCap || 'N/A'}</span>
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
                    <div className="member-field full-width">
                        <span className="label">Address</span>
                        <span className="value">{member.address || 'N/A'}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
