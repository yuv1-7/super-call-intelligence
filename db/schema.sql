-- db/schema.sql — One-time DDL script to create CallIQ database tables
-- Run: psql -U postgres -d calliq -f db/schema.sql

BEGIN;

-- ══════════════════════════════════════════════
-- TEAMS
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS teams (
    id              TEXT PRIMARY KEY,                  -- e.g. 'team_alpha'
    name            TEXT NOT NULL,                     -- e.g. 'Team Alpha'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ══════════════════════════════════════════════
-- USERS (synced from Clerk — role/team stored here for queries)
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    clerk_user_id   TEXT PRIMARY KEY,                  -- Clerk user ID (e.g. 'user_2x...')
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('agent', 'team_lead', 'manager')),
    team_id         TEXT REFERENCES teams(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ══════════════════════════════════════════════
-- POLICIES (insurance members / policyholders)
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS policies (
    policy_id       TEXT PRIMARY KEY,                  -- e.g. 'CAR-100001'
    name            TEXT NOT NULL,
    age             INTEGER,
    phone           TEXT,
    email           TEXT,
    policy_type     TEXT NOT NULL,                     -- e.g. 'Car Insurance — Comprehensive'
    coverage_type   TEXT,
    coverage_amount INTEGER,
    premium         INTEGER,
    deductible      INTEGER,
    status          TEXT NOT NULL DEFAULT 'Active',
    start_date      DATE,
    end_date        TEXT,                              -- TEXT because life policies can be 'Lifetime'
    -- Policy-type-specific JSONB columns
    vehicle         JSONB,                             -- Car only: {make, model, year, color, vin, licensePlate}
    beneficiaries   JSONB,                             -- Life only: [{name, relationship, share}]
    sub_limits      JSONB,                             -- Medical only: {roomRent, icu, ambulance}
    claim_history   JSONB NOT NULL DEFAULT '[]'::JSONB,-- [{claimId, date, type, amount, status}]
    add_ons         JSONB NOT NULL DEFAULT '[]'::JSONB,-- ["Roadside Assistance", ...]
    -- Life-specific
    contestability_expired  BOOLEAN,
    medical_history         TEXT,
    last_premium_paid       TEXT,
    cash_value              INTEGER,
    -- Medical-specific
    network_hospitals       JSONB,                     -- ["Hospital A", ...]
    room_category           TEXT,
    copay                   INTEGER,
    pre_existing_waiting    TEXT,
    maternity               BOOLEAN,
    day_care_procedures     BOOLEAN,
    covered_conditions      JSONB,                     -- ["Cancer", "Stroke", ...]
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policies_phone ON policies(phone);

-- ══════════════════════════════════════════════
-- CALLS (call history)
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS calls (
    id              SERIAL PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    policy_id       TEXT REFERENCES policies(policy_id) ON DELETE SET NULL,
    start_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_secs   INTEGER,
    intent          TEXT,                               -- e.g. 'car_accident'
    claim_type      TEXT,                               -- e.g. 'car_insurance'
    transcript      JSONB NOT NULL DEFAULT '[]'::JSONB, -- [{speaker, text, timestamp, offset}]
    accumulated_facts JSONB,                            -- {date_of_incident, location, ...}
    member_snapshot JSONB,                              -- Snapshot of member data at call time
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calls_agent_id ON calls(agent_id);
CREATE INDEX IF NOT EXISTS idx_calls_start_time ON calls(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_calls_claim_type ON calls(claim_type);

-- ══════════════════════════════════════════════
-- EVALUATIONS (post-call evaluation results)
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS evaluations (
    id              SERIAL PRIMARY KEY,
    call_id         INTEGER NOT NULL UNIQUE REFERENCES calls(id) ON DELETE CASCADE,
    overall_score   INTEGER NOT NULL,
    grade           TEXT NOT NULL,                      -- 'Exceptional', 'Proficient', etc.
    -- Rubric data
    sections        JSONB NOT NULL,                     -- 7 scored sections array
    auto_fails      JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Insights data
    call_type       TEXT,
    call_outcome    TEXT,
    call_summary    TEXT,
    call_events     JSONB,
    caller_insights JSONB,
    skill_observations  JSONB,
    procedure_gaps      JSONB,
    strong_moments      JSONB,
    compliance_flags    JSONB,
    compliance_summary  TEXT,
    missed_opportunities JSONB,
    recurring_risk_indicators JSONB,
    positive_indicators      JSONB,
    agent_improvement_notes  JSONB,
    -- FNOL completeness
    fnol_completeness_pct   INTEGER,
    fnol_points_earned      INTEGER,
    fnol_points_possible    INTEGER,
    fnol_fields_collected   JSONB,
    fnol_fields_missing     JSONB,
    -- Metadata
    total_utterances    INTEGER,
    agent_utterances    INTEGER,
    customer_utterances INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluations_call_id ON evaluations(call_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_overall_score ON evaluations(overall_score);

COMMIT;
