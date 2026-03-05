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

    // Determine policy type from policy_number prefix (NS-, CAR-, LIFE-)
    const policyNumber = member.policy_number || '';
    const isLifePolicy = policyNumber.toUpperCase().startsWith('LIFE');

    // Coverage limits
    const limits = member.coverage_limits || {};
    const collisionDeductible = limits.collision_deductible || 'N/A';
    const comprehensiveDeductible = limits.comprehensive_deductible || 'N/A';
    const bodilyInjury = limits.bodily_injury || 'N/A';
    const propertyDamage = limits.property_damage || 'N/A';

    // Add-ons
    const addOns = member.add_ons || [];

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

                    {/* Vehicle — shown for all non-life policies */}
                    {!isLifePolicy && member.vehicle && (
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

                    {/* Coverage limits */}
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

                    {/* Add-ons */}
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
