# db/queries.py — Async database query helpers for CallIQ

import re
import json
import logging
from db.connection import get_pool

logger = logging.getLogger("call-intelligence")


# ══════════════════════════════════════════════
# POLICY / MEMBER QUERIES
# ══════════════════════════════════════════════

def _row_to_member_dict(row) -> dict | None:
    """Convert a policies DB row to the frontend-compatible member dict.
    
    Maps snake_case DB columns to camelCase keys matching the existing
    frontend contract (MemberCard.jsx expects camelCase).
    """
    if row is None:
        return None

    member = {
        "policyId": row["policy_id"],
        "name": row["name"],
        "age": row["age"],
        "phone": row["phone"],
        "email": row["email"],
        "policyType": row["policy_type"],
        "coverageType": row["coverage_type"],
        "coverageAmount": row["coverage_amount"],
        "premium": row["premium"],
        "deductible": row["deductible"],
        "status": row["status"],
        "startDate": str(row["start_date"]) if row["start_date"] else None,
        "endDate": row["end_date"],
        "claimHistory": json.loads(row["claim_history"]) if isinstance(row["claim_history"], str) else row["claim_history"],
        "addOns": json.loads(row["add_ons"]) if isinstance(row["add_ons"], str) else row["add_ons"],
    }

    # Car-specific
    if row["vehicle"]:
        vehicle = json.loads(row["vehicle"]) if isinstance(row["vehicle"], str) else row["vehicle"]
        member["vehicle"] = vehicle

    # Life-specific
    if row["beneficiaries"]:
        beneficiaries = json.loads(row["beneficiaries"]) if isinstance(row["beneficiaries"], str) else row["beneficiaries"]
        member["beneficiaries"] = beneficiaries
    if row["contestability_expired"] is not None:
        member["contestabilityExpired"] = row["contestability_expired"]
    if row["medical_history"]:
        member["medicalHistory"] = row["medical_history"]
    if row["last_premium_paid"]:
        member["lastPremiumPaid"] = row["last_premium_paid"]
    if row["cash_value"] is not None:
        member["cashValue"] = row["cash_value"]

    # Medical-specific
    if row["network_hospitals"]:
        hospitals = json.loads(row["network_hospitals"]) if isinstance(row["network_hospitals"], str) else row["network_hospitals"]
        member["networkHospitals"] = hospitals
    if row["room_category"]:
        member["roomCategory"] = row["room_category"]
    if row["copay"] is not None:
        member["copay"] = row["copay"]
    if row["pre_existing_waiting"]:
        member["preExistingWaiting"] = row["pre_existing_waiting"]
    if row["maternity"] is not None:
        member["maternity"] = row["maternity"]
    if row["day_care_procedures"] is not None:
        member["dayCareProcedures"] = row["day_care_procedures"]
    if row["sub_limits"]:
        sub_limits = json.loads(row["sub_limits"]) if isinstance(row["sub_limits"], str) else row["sub_limits"]
        if sub_limits:  # Don't include empty {}
            member["subLimits"] = sub_limits
    if row["covered_conditions"]:
        conditions = json.loads(row["covered_conditions"]) if isinstance(row["covered_conditions"], str) else row["covered_conditions"]
        member["coveredConditions"] = conditions

    return member


async def get_policy(policy_id: str) -> dict | None:
    """Fetch a policy by its ID. Returns camelCase dict or None."""
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM policies WHERE policy_id = $1", policy_id.upper().strip())
    return _row_to_member_dict(row)


async def get_policy_by_phone(phone: str) -> dict | None:
    """Fetch a policy by phone number. Strips non-digits for matching."""
    search_phone = re.sub(r'\D', '', phone)
    if len(search_phone) < 10:
        return None

    pool = get_pool()
    # Use postgres regexp_replace to strip non-digits for comparison
    row = await pool.fetchrow(
        "SELECT * FROM policies WHERE regexp_replace(phone, '[^0-9]', '', 'g') LIKE $1 LIMIT 1",
        f"%{search_phone}%"
    )
    if row:
        return _row_to_member_dict(row)
    return None


async def get_all_policies() -> list[dict]:
    """Fetch all policies. Returns list of camelCase dicts."""
    pool = get_pool()
    rows = await pool.fetch("SELECT * FROM policies ORDER BY policy_id")
    return [_row_to_member_dict(row) for row in rows]


# ══════════════════════════════════════════════
# CALL QUERIES
# ══════════════════════════════════════════════

async def save_call(
    agent_id: str,
    policy_id: str | None,
    duration_secs: int,
    intent: str | None,
    claim_type: str | None,
    transcript: list,
    accumulated_facts: dict | None,
    member_data: dict | None,
) -> int:
    """Save a completed call. Returns the call ID."""
    pool = get_pool()
    call_id = await pool.fetchval(
        """
        INSERT INTO calls (agent_id, policy_id, duration_secs, intent, claim_type,
                          transcript, accumulated_facts, member_snapshot)
        VALUES ($1, $2, $3, $4, $5, $6::JSONB, $7::JSONB, $8::JSONB)
        RETURNING id
        """,
        agent_id,
        policy_id,
        duration_secs,
        intent,
        claim_type,
        json.dumps(transcript),
        json.dumps(accumulated_facts) if accumulated_facts else None,
        json.dumps(member_data) if member_data else None,
    )
    logger.info(f"💾 Saved call #{call_id} for agent {agent_id}")
    return call_id


async def save_evaluation(call_id: int, evaluation: dict) -> int:
    """Save a post-call evaluation linked to a call. Returns evaluation ID."""
    pool = get_pool()
    eval_id = await pool.fetchval(
        """
        INSERT INTO evaluations (
            call_id, overall_score, grade,
            sections, auto_fails,
            call_type, call_outcome, call_summary, call_events,
            caller_insights, skill_observations, procedure_gaps, strong_moments,
            compliance_flags, compliance_summary,
            missed_opportunities, recurring_risk_indicators,
            positive_indicators, agent_improvement_notes,
            fnol_completeness_pct, fnol_points_earned, fnol_points_possible,
            fnol_fields_collected, fnol_fields_missing,
            total_utterances, agent_utterances, customer_utterances
        ) VALUES (
            $1, $2, $3,
            $4::JSONB, $5::JSONB,
            $6, $7, $8, $9::JSONB,
            $10::JSONB, $11::JSONB, $12::JSONB, $13::JSONB,
            $14::JSONB, $15,
            $16::JSONB, $17::JSONB,
            $18::JSONB, $19::JSONB,
            $20, $21, $22,
            $23::JSONB, $24::JSONB,
            $25, $26, $27
        )
        RETURNING id
        """,
        call_id,
        evaluation.get("overall_score", 0),
        evaluation.get("grade", "N/A"),
        json.dumps(evaluation.get("sections", [])),
        json.dumps(evaluation.get("auto_fails", [])),
        evaluation.get("call_type"),
        evaluation.get("call_outcome"),
        evaluation.get("call_summary"),
        json.dumps(evaluation.get("call_events", [])),
        json.dumps(evaluation.get("caller_insights", {})),
        json.dumps(evaluation.get("skill_observations", [])),
        json.dumps(evaluation.get("procedure_gaps", [])),
        json.dumps(evaluation.get("strong_moments", [])),
        json.dumps(evaluation.get("compliance_flags", [])),
        evaluation.get("compliance_summary"),
        json.dumps(evaluation.get("missed_opportunities", [])),
        json.dumps(evaluation.get("recurring_risk_indicators", [])),
        json.dumps(evaluation.get("positive_indicators", [])),
        json.dumps(evaluation.get("agent_improvement_notes", [])),
        evaluation.get("fnol_completeness_pct", 0),
        evaluation.get("fnol_points_earned", 0),
        evaluation.get("fnol_points_possible", 0),
        json.dumps(evaluation.get("fnol_fields_collected", [])),
        json.dumps(evaluation.get("fnol_fields_missing", [])),
        evaluation.get("total_utterances", 0),
        evaluation.get("agent_utterances", 0),
        evaluation.get("customer_utterances", 0),
    )
    logger.info(f"💾 Saved evaluation #{eval_id} for call #{call_id}")
    return eval_id


async def get_calls(agent_id: str | None = None, team_id: str | None = None, role: str = "agent", limit: int = 50, offset: int = 0, claim_type: str | None = None) -> list[dict]:
    """Fetch call history filtered by role.
    
    - agent: only own calls
    - team_lead: all calls from agents in their team
    - manager: all calls
    
    Optional claim_type filter for server-side filtering with correct pagination.
    """
    pool = get_pool()

    # Build optional claim_type filter clause
    claim_filter = ""

    if role == "manager":
        params = []
        base_where = ""
        if claim_type:
            base_where = "WHERE c.claim_type = $1"
            params = [claim_type, limit, offset]
        else:
            params = [limit, offset]
        rows = await pool.fetch(
            f"""
            SELECT c.*, u.name as agent_name, u.team_id,
                   e.overall_score, e.grade
            FROM calls c
            JOIN users u ON c.agent_id = u.clerk_user_id
            LEFT JOIN evaluations e ON e.call_id = c.id
            {base_where}
            ORDER BY c.start_time DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params
        )
    elif role == "team_lead" and team_id:
        if claim_type:
            params = [team_id, claim_type, limit, offset]
            where_clause = "WHERE u.team_id = $1 AND c.claim_type = $2"
        else:
            params = [team_id, limit, offset]
            where_clause = "WHERE u.team_id = $1"
        rows = await pool.fetch(
            f"""
            SELECT c.*, u.name as agent_name, u.team_id,
                   e.overall_score, e.grade
            FROM calls c
            JOIN users u ON c.agent_id = u.clerk_user_id
            LEFT JOIN evaluations e ON e.call_id = c.id
            {where_clause}
            ORDER BY c.start_time DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params
        )
    else:
        if claim_type:
            params = [agent_id, claim_type, limit, offset]
            where_clause = "WHERE c.agent_id = $1 AND c.claim_type = $2"
        else:
            params = [agent_id, limit, offset]
            where_clause = "WHERE c.agent_id = $1"
        rows = await pool.fetch(
            f"""
            SELECT c.*, u.name as agent_name, u.team_id,
                   e.overall_score, e.grade
            FROM calls c
            JOIN users u ON c.agent_id = u.clerk_user_id
            LEFT JOIN evaluations e ON e.call_id = c.id
            {where_clause}
            ORDER BY c.start_time DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params
        )

    return [_call_row_to_dict(row) for row in rows]


def _call_row_to_dict(row) -> dict:
    """Convert a calls DB row to a JSON-serializable dict."""
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "agent_name": row.get("agent_name", ""),
        "team_id": row.get("team_id"),
        "policy_id": row["policy_id"],
        "start_time": row["start_time"].isoformat() if row["start_time"] else None,
        "duration_secs": row["duration_secs"],
        "intent": row["intent"],
        "claim_type": row["claim_type"],
        "transcript": json.loads(row["transcript"]) if isinstance(row["transcript"], str) else row["transcript"],
        "accumulated_facts": json.loads(row["accumulated_facts"]) if isinstance(row["accumulated_facts"], str) else row["accumulated_facts"],
        "member_snapshot": json.loads(row["member_snapshot"]) if isinstance(row["member_snapshot"], str) else row["member_snapshot"],
        "overall_score": row.get("overall_score"),
        "grade": row.get("grade"),
    }


async def get_call_with_evaluation(call_id: int, agent_id: str | None = None, team_id: str | None = None, role: str = "agent") -> dict | None:
    """Fetch a single call with its full evaluation, respecting role access."""
    pool = get_pool()

    row = await pool.fetchrow(
        """
        SELECT c.*, u.name as agent_name, u.team_id
        FROM calls c
        JOIN users u ON c.agent_id = u.clerk_user_id
        WHERE c.id = $1
        """,
        call_id
    )
    if not row:
        return None

    # Check access
    if role == "agent" and row["agent_id"] != agent_id:
        return None
    if role == "team_lead" and row["team_id"] != team_id:
        return None
    # manager can see all

    call = _call_row_to_dict(row)

    # Fetch evaluation
    eval_row = await pool.fetchrow("SELECT * FROM evaluations WHERE call_id = $1", call_id)
    if eval_row:
        call["evaluation"] = _eval_row_to_dict(eval_row)

    return call


async def delete_call(call_id: int, agent_id: str | None = None, team_id: str | None = None, role: str = "agent") -> bool:
    """Delete a call record, respecting role access."""
    pool = get_pool()

    # Verify access first
    row = await pool.fetchrow(
        """
        SELECT c.agent_id, u.team_id
        FROM calls c
        JOIN users u ON c.agent_id = u.clerk_user_id
        WHERE c.id = $1
        """,
        call_id
    )
    if not row:
        return False

    can_delete = False
    if role == "manager":
        can_delete = True
    elif role == "team_lead" and row["team_id"] == team_id:
        can_delete = True
    elif role == "agent" and row["agent_id"] == agent_id:
        can_delete = True

    if not can_delete:
        logger.warning(f"🚫 Unauthorized delete attempt for call #{call_id} by {agent_id} (role: {role})")
        return False

    await pool.execute("DELETE FROM calls WHERE id = $1", call_id)
    logger.info(f"🗑️ Deleted call #{call_id}")
    return True


def _eval_row_to_dict(row) -> dict:
    """Convert an evaluations DB row to a JSON-serializable dict."""
    def _parse(val):
        if isinstance(val, str):
            return json.loads(val)
        return val

    return {
        "id": row["id"],
        "call_id": row["call_id"],
        "overall_score": row["overall_score"],
        "grade": row["grade"],
        "sections": _parse(row["sections"]),
        "auto_fails": _parse(row["auto_fails"]),
        "call_type": row["call_type"],
        "call_outcome": row["call_outcome"],
        "call_summary": row["call_summary"],
        "call_events": _parse(row["call_events"]),
        "caller_insights": _parse(row["caller_insights"]),
        "skill_observations": _parse(row["skill_observations"]),
        "procedure_gaps": _parse(row["procedure_gaps"]),
        "strong_moments": _parse(row["strong_moments"]),
        "compliance_flags": _parse(row["compliance_flags"]),
        "compliance_summary": row["compliance_summary"],
        "missed_opportunities": _parse(row["missed_opportunities"]),
        "recurring_risk_indicators": _parse(row["recurring_risk_indicators"]),
        "positive_indicators": _parse(row["positive_indicators"]),
        "agent_improvement_notes": _parse(row["agent_improvement_notes"]),
        "fnol_completeness_pct": row["fnol_completeness_pct"],
        "fnol_points_earned": row["fnol_points_earned"],
        "fnol_points_possible": row["fnol_points_possible"],
        "fnol_fields_collected": _parse(row["fnol_fields_collected"]),
        "fnol_fields_missing": _parse(row["fnol_fields_missing"]),
        "total_utterances": row["total_utterances"],
        "agent_utterances": row["agent_utterances"],
        "customer_utterances": row["customer_utterances"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


# ══════════════════════════════════════════════
# ANALYTICS / SUMMARY QUERIES
# ══════════════════════════════════════════════

async def get_evaluation_summary(agent_id: str | None = None, team_id: str | None = None, role: str = "agent") -> dict:
    """Get aggregate evaluation stats filtered by role."""
    pool = get_pool()

    if role == "manager":
        row = await pool.fetchrow(
            """
            SELECT COUNT(e.id) as total_calls,
                   COALESCE(AVG(e.overall_score), 0) as avg_score,
                   MIN(e.overall_score) as min_score,
                   MAX(e.overall_score) as max_score
            FROM evaluations e
            JOIN calls c ON e.call_id = c.id
            """
        )
    elif role == "team_lead" and team_id:
        row = await pool.fetchrow(
            """
            SELECT COUNT(e.id) as total_calls,
                   COALESCE(AVG(e.overall_score), 0) as avg_score,
                   MIN(e.overall_score) as min_score,
                   MAX(e.overall_score) as max_score
            FROM evaluations e
            JOIN calls c ON e.call_id = c.id
            JOIN users u ON c.agent_id = u.clerk_user_id
            WHERE u.team_id = $1
            """,
            team_id
        )
    else:
        row = await pool.fetchrow(
            """
            SELECT COUNT(e.id) as total_calls,
                   COALESCE(AVG(e.overall_score), 0) as avg_score,
                   MIN(e.overall_score) as min_score,
                   MAX(e.overall_score) as max_score
            FROM evaluations e
            JOIN calls c ON e.call_id = c.id
            WHERE c.agent_id = $1
            """,
            agent_id
        )

    # Grade distribution
    if role == "manager":
        grade_rows = await pool.fetch(
            "SELECT grade, COUNT(*) as count FROM evaluations GROUP BY grade"
        )
    elif role == "team_lead" and team_id:
        grade_rows = await pool.fetch(
            """
            SELECT e.grade, COUNT(*) as count
            FROM evaluations e
            JOIN calls c ON e.call_id = c.id
            JOIN users u ON c.agent_id = u.clerk_user_id
            WHERE u.team_id = $1
            GROUP BY e.grade
            """,
            team_id
        )
    else:
        grade_rows = await pool.fetch(
            """
            SELECT e.grade, COUNT(*) as count
            FROM evaluations e
            JOIN calls c ON e.call_id = c.id
            WHERE c.agent_id = $1
            GROUP BY e.grade
            """,
            agent_id
        )

    return {
        "total_calls": row["total_calls"],
        "avg_score": round(float(row["avg_score"]), 1),
        "min_score": row["min_score"],
        "max_score": row["max_score"],
        "grade_distribution": {r["grade"]: r["count"] for r in grade_rows},
    }


async def get_team_members(team_id: str) -> list[dict]:
    """Get all users in a team."""
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT clerk_user_id, name, email, role FROM users WHERE team_id = $1 ORDER BY role, name",
        team_id
    )
    return [dict(row) for row in rows]


async def get_all_teams() -> list[dict]:
    """Get all teams with member counts."""
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT t.id, t.name, COUNT(u.clerk_user_id) as member_count
        FROM teams t
        LEFT JOIN users u ON u.team_id = t.id
        GROUP BY t.id, t.name
        ORDER BY t.name
        """
    )
    return [dict(row) for row in rows]


async def get_team_performance(team_id: str | None = None) -> list[dict]:
    """Get per-agent performance stats. If team_id is None, returns all agents."""
    pool = get_pool()

    query = """
        SELECT u.clerk_user_id, u.name, u.team_id,
               COUNT(e.id) as total_calls,
               COALESCE(AVG(e.overall_score), 0) as avg_score
        FROM users u
        LEFT JOIN calls c ON c.agent_id = u.clerk_user_id
        LEFT JOIN evaluations e ON e.call_id = c.id
        WHERE u.role IN ('agent', 'team_lead')
    """
    params = []
    if team_id:
        query += " AND u.team_id = $1"
        params.append(team_id)

    query += " GROUP BY u.clerk_user_id, u.name, u.team_id ORDER BY avg_score DESC"

    rows = await pool.fetch(query, *params)
    return [{
        "clerk_user_id": r["clerk_user_id"],
        "name": r["name"],
        "team_id": r["team_id"],
        "total_calls": r["total_calls"],
        "avg_score": round(float(r["avg_score"]), 1),
    } for r in rows]


# ══════════════════════════════════════════════
# AGENT DRILL-DOWN QUERIES
# ══════════════════════════════════════════════

async def get_agent_calls_for_team(clerk_user_id: str, team_id: str | None = None, limit: int = 10) -> dict:
    """Get a specific agent's calls and summary stats (for team lead / manager drill-down).
    If team_id is provided, restrict to that team only (for team leads).
    """
    pool = get_pool()

    # If team_id is set, verify agent belongs to that team
    if team_id:
        agent = await pool.fetchrow(
            "SELECT clerk_user_id FROM users WHERE clerk_user_id = $1 AND team_id = $2",
            clerk_user_id, team_id
        )
        if not agent:
            return {"calls": [], "summary": {}}

    # Get recent calls with evaluations
    rows = await pool.fetch("""
        SELECT c.id, c.intent, c.start_time, c.duration_secs,
               e.overall_score, e.grade
        FROM calls c
        LEFT JOIN evaluations e ON e.call_id = c.id
        WHERE c.agent_id = $1
        ORDER BY c.start_time DESC NULLS LAST
        LIMIT $2
    """, clerk_user_id, limit)

    calls = [{
        "id": str(r["id"]),
        "intent": r["intent"],
        "start_time": r["start_time"].isoformat() if r["start_time"] else None,
        "duration_secs": r["duration_secs"],
        "overall_score": r["overall_score"],
        "grade": r["grade"],
    } for r in rows]

    # Get summary stats
    stats = await pool.fetchrow("""
        SELECT COUNT(*) as total_calls,
               COALESCE(AVG(e.overall_score), 0) as avg_score,
               MAX(e.overall_score) as max_score,
               MIN(e.overall_score) as min_score
        FROM calls c
        LEFT JOIN evaluations e ON e.call_id = c.id
        WHERE c.agent_id = $1
    """, clerk_user_id)

    summary = {
        "total_calls": stats["total_calls"],
        "avg_score": round(float(stats["avg_score"]), 1),
        "max_score": stats["max_score"],
        "min_score": stats["min_score"],
    }

    return {"calls": calls, "summary": summary}


# ══════════════════════════════════════════════
# USER QUERIES
# ══════════════════════════════════════════════

async def get_user(clerk_user_id: str) -> dict | None:
    """Get a user by Clerk user ID."""
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE clerk_user_id = $1",
        clerk_user_id
    )
    if not row:
        return None
    return dict(row)


async def upsert_user(clerk_user_id: str, name: str, email: str, role: str = "agent", team_id: str | None = None) -> dict:
    """Insert or update a user from Clerk data."""
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO users (clerk_user_id, name, email, role, team_id)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (clerk_user_id) DO UPDATE SET
            name = EXCLUDED.name,
            email = EXCLUDED.email,
            role = EXCLUDED.role,
            team_id = EXCLUDED.team_id
        RETURNING *
        """,
        clerk_user_id, name, email, role, team_id
    )
    return dict(row)


# ══════════════════════════════════════════════
# DEV / ADMIN QUERIES
# ══════════════════════════════════════════════

async def delete_call(call_id: int, agent_id: str, role: str) -> bool:
    """Delete a single call (and its evaluation via CASCADE).
    Agents can only delete their own calls; leads/managers can delete any."""
    pool = get_pool()
    if role == "agent":
        result = await pool.execute(
            "DELETE FROM calls WHERE id = $1 AND agent_id = $2",
            call_id, agent_id
        )
    else:
        result = await pool.execute("DELETE FROM calls WHERE id = $1", call_id)
    deleted = int(result.split()[-1])
    logger.info(f"🗑️ Deleted call {call_id} (rows={deleted})")
    return deleted > 0


async def clear_call_history() -> int:
    """Delete all calls and their evaluations. Returns count of deleted calls."""
    pool = get_pool()
    result = await pool.execute("DELETE FROM calls")
    count = int(result.split()[-1])
    logger.info(f"🗑️ Cleared {count} call records")
    return count




async def clear_evaluations() -> int:
    """Delete all evaluations only. Returns count."""
    pool = get_pool()
    result = await pool.execute("DELETE FROM evaluations")
    count = int(result.split()[-1])
    logger.info(f"🗑️ Cleared {count} evaluation records")
    return count


async def get_db_stats() -> dict:
    """Get DB table counts for dev dashboard."""
    pool = get_pool()
    stats = {}
    for table in ["teams", "users", "policies", "calls", "evaluations"]:
        count = await pool.fetchval(f"SELECT COUNT(*) FROM {table}")
        stats[table] = count
    return stats
