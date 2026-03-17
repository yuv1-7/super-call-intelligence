-- db/seed.sql — One-time data population script for CallIQ
-- Run AFTER schema.sql: psql -U postgres -d calliq -f db/seed.sql
-- 
-- NOTE: Update the clerk_user_id values below to match your actual Clerk user IDs
--       after creating accounts in the Clerk Dashboard.

BEGIN;

-- ══════════════════════════════════════════════
-- TEAMS
-- ══════════════════════════════════════════════
INSERT INTO teams (id, name) VALUES
    ('team_alpha', 'Team Alpha'),
    ('team_beta',  'Team Beta')
ON CONFLICT (id) DO NOTHING;

-- ══════════════════════════════════════════════
-- USERS (replace clerk_user_id with real Clerk IDs)
-- ══════════════════════════════════════════════
INSERT INTO users (clerk_user_id, name, email, role, team_id) VALUES
    ('clerk_agent_001',     'Alice Johnson',    'alice@calliq.com',     'agent',     'team_alpha'),
    ('clerk_agent_002',     'Bob Martinez',     'bob@calliq.com',       'agent',     'team_alpha'),
    ('clerk_agent_003',     'Carla Davis',      'carla@calliq.com',     'agent',     'team_beta'),
    ('clerk_lead_001',      'Derek Wang',       'derek@calliq.com',     'team_lead', 'team_alpha'),
    ('clerk_lead_002',      'Elena Foster',     'elena@calliq.com',     'team_lead', 'team_beta'),
    ('clerk_manager_001',   'Frank Reynolds',   'frank@calliq.com',     'manager',    NULL)
ON CONFLICT (clerk_user_id) DO NOTHING;

-- ══════════════════════════════════════════════
-- POLICIES — CAR INSURANCE
-- ══════════════════════════════════════════════
INSERT INTO policies (
    policy_id, name, age, phone, email, policy_type, coverage_type,
    coverage_amount, premium, deductible, status, start_date, end_date,
    vehicle, claim_history, add_ons
) VALUES
(
    'CAR-100001', 'Michael T. Henderson', 42, '(555) 019-8372', 'michael.henderson@email.com',
    'Car Insurance — Comprehensive', 'Comprehensive',
    300000, 2400, 500, 'Active', '2025-03-01', '2026-03-01',
    '{"make": "Honda", "model": "Accord EX-L", "year": 2021, "color": "Lunar Silver Metallic", "vin": "1HGCM82633A001234", "licensePlate": "OH-HRP-4821"}'::JSONB,
    '[{"claimId": "CLM-5001", "date": "2025-09-15", "type": "Minor Fender Bender", "amount": 3200, "status": "Settled"}]'::JSONB,
    '["Roadside Assistance", "Rental Reimbursement"]'::JSONB
),
(
    'CAR-100002', 'Sarah Jenkins', 29, '(555) 014-9921', 'sarah.jenkins@email.com',
    'Car Insurance — Third Party', 'Third Party Only',
    100000, 1200, 1000, 'Active', '2025-06-15', '2026-06-15',
    '{"make": "Toyota", "model": "RAV4 LE", "year": 2018, "color": "Midnight Blue", "vin": "2T1BR32E91C123456", "licensePlate": "WA-SJK-7733"}'::JSONB,
    '[]'::JSONB,
    '[]'::JSONB
),
(
    'CAR-100003', 'David Alvez', 54, '(555) 017-4433', 'david.alvez@email.com',
    'Car Insurance — Comprehensive', 'Comprehensive + Collision',
    500000, 3600, 250, 'Active', '2025-01-10', '2026-01-10',
    '{"make": "Ford", "model": "F-150 Lariat", "year": 2023, "color": "Agate Black", "vin": "1FTFW1E88PK192837", "licensePlate": "AZ-DAL-2109"}'::JSONB,
    '[{"claimId": "CLM-5010", "date": "2025-04-20", "type": "Windshield Replacement", "amount": 850, "status": "Settled"}, {"claimId": "CLM-5011", "date": "2025-11-05", "type": "Rear-End Collision", "amount": 12500, "status": "Under Review"}]'::JSONB,
    '["Roadside Assistance", "Zero Depreciation", "Engine Protection", "Passenger Cover", "Rental Reimbursement"]'::JSONB
)
ON CONFLICT (policy_id) DO NOTHING;

-- ══════════════════════════════════════════════
-- POLICIES — LIFE INSURANCE
-- ══════════════════════════════════════════════
INSERT INTO policies (
    policy_id, name, age, phone, email, policy_type, coverage_type,
    coverage_amount, premium, status, start_date, end_date,
    beneficiaries, contestability_expired, medical_history, last_premium_paid,
    claim_history, add_ons
) VALUES
(
    'LIFE-200001', 'Robert J. Whitfield', 62, '(555) 022-6891', 'robert.whitfield@email.com',
    'Life Insurance — Term Life', 'Term Life (20 Year)',
    500000, 4800, 'Active', '2015-05-20', '2035-05-20',
    '[{"name": "Margaret Whitfield", "relationship": "Spouse", "share": "60%"}, {"name": "James Whitfield", "relationship": "Son", "share": "40%"}]'::JSONB,
    TRUE, 'Non-smoker, no pre-existing conditions at time of policy inception', '2026-01-20',
    '[]'::JSONB, '[]'::JSONB
),
(
    'LIFE-200002', 'Catherine M. Brooks', 38, '(555) 033-7742', 'catherine.brooks@email.com',
    'Life Insurance — Whole Life', 'Whole Life with Cash Value',
    1000000, 9600, 'Active', '2020-08-01', 'Lifetime',
    '[{"name": "Daniel Brooks", "relationship": "Spouse", "share": "100%"}]'::JSONB,
    TRUE, 'Non-smoker, mild asthma managed with medication', '2026-02-01',
    '[]'::JSONB, '[]'::JSONB
),
(
    'LIFE-200003', 'Marcus A. Rivera', 29, '(555) 044-8853', 'marcus.rivera@email.com',
    'Life Insurance — Accidental Death & Dismemberment', 'AD&D',
    750000, 1800, 'Active', '2025-11-01', '2026-11-01',
    '[{"name": "Elena Rivera", "relationship": "Spouse", "share": "50%"}, {"name": "Rosa Rivera", "relationship": "Mother", "share": "50%"}]'::JSONB,
    FALSE, 'Healthy, active lifestyle, no pre-existing conditions', '2026-02-01',
    '[]'::JSONB, '[]'::JSONB
)
ON CONFLICT (policy_id) DO NOTHING;

-- Update cash_value for LIFE-200002 (Whole Life policy)
UPDATE policies SET cash_value = 42500 WHERE policy_id = 'LIFE-200002';

-- ══════════════════════════════════════════════
-- POLICIES — MEDICAL INSURANCE
-- ══════════════════════════════════════════════
INSERT INTO policies (
    policy_id, name, age, phone, email, policy_type, coverage_type,
    coverage_amount, premium, deductible, status, start_date, end_date,
    network_hospitals, room_category, copay, pre_existing_waiting,
    maternity, day_care_procedures, sub_limits,
    claim_history, add_ons
) VALUES
(
    'MED-300001', 'Karen L. Mitchell', 42, '(555) 055-3214', 'karen.mitchell@email.com',
    'Medical Insurance — Individual Health', 'Individual Health (PPO)',
    500000, 6200, 2500, 'Active', '2025-04-01', '2026-04-01',
    '["Mount Sinai Hospital", "NYU Langone Health", "NewYork-Presbyterian", "Memorial Sloan Kettering"]'::JSONB,
    'Private', 10, 'Completed — 4-year waiting period expired',
    FALSE, TRUE,
    '{"roomRent": "$1,200/day", "icu": "$2,500/day", "ambulance": "$500 per trip"}'::JSONB,
    '[{"claimId": "CLM-M-7001", "date": "2025-08-10", "type": "ER Visit — Allergic Reaction", "amount": 4500, "status": "Settled"}]'::JSONB,
    '["Day-Care Procedures", "Ambulance Cover"]'::JSONB
),
(
    'MED-300002', 'Thomas R. Nguyen', 55, '(555) 066-9875', 'thomas.nguyen@email.com',
    'Medical Insurance — Family Plan', 'Family Plan (HMO)',
    1000000, 14400, 5000, 'Active', '2025-07-01', '2026-07-01',
    '["Mayo Clinic", "Cleveland Clinic", "Johns Hopkins Hospital", "Massachusetts General Hospital"]'::JSONB,
    'Semi-Private', 20, 'Active — 2 years remaining (Type 2 Diabetes disclosed)',
    TRUE, TRUE,
    '{"roomRent": "$800/day", "icu": "$1,800/day", "ambulance": "$400 per trip"}'::JSONB,
    '[{"claimId": "CLM-M-7010", "date": "2025-09-20", "type": "Knee Arthroscopy (Day-Care)", "amount": 8500, "status": "Settled"}, {"claimId": "CLM-M-7011", "date": "2025-12-05", "type": "Spouse — Appendectomy", "amount": 32000, "status": "Under Review"}]'::JSONB,
    '["Day-Care Procedures", "Maternity Cover", "Ambulance Cover", "OPD Cover"]'::JSONB
),
(
    'MED-300003', 'Jennifer S. Park', 34, '(555) 077-6543', 'jennifer.park@email.com',
    'Medical Insurance — Critical Illness', 'Critical Illness',
    500000, 3600, 0, 'Active', '2025-01-15', '2026-01-15',
    '["MD Anderson Cancer Center", "Memorial Sloan Kettering", "Dana-Farber Cancer Institute"]'::JSONB,
    'Private', 0, 'Completed — no waiting period applicable',
    FALSE, FALSE,
    '{}'::JSONB,
    '[]'::JSONB,
    '[]'::JSONB
)
ON CONFLICT (policy_id) DO NOTHING;

-- Add covered conditions for MED-300003
UPDATE policies SET covered_conditions = '["Cancer", "Heart Attack", "Stroke", "Kidney Failure", "Major Organ Transplant", "Multiple Sclerosis"]'::JSONB
WHERE policy_id = 'MED-300003';

COMMIT;
