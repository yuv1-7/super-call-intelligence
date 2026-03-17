# data/members.py — Policy Lookup (Database-backed with in-memory fallback)
# Queries PostgreSQL for member/policy data. Falls back to hardcoded
# data if DATABASE_URL is not configured (dev/testing convenience).

import re
import logging

logger = logging.getLogger("call-intelligence")

# ─── In-memory fallback data (used when DB is not configured) ─── #
MEMBER_DB = {
    # ─── CAR INSURANCE POLICIES ─── #
    "CAR-100001": {
        "policyId": "CAR-100001",
        "name": "Michael T. Henderson",
        "age": 42,
        "phone": "(555) 019-8372",
        "email": "michael.henderson@email.com",
        "policyType": "Car Insurance — Comprehensive",
        "coverageType": "Comprehensive",
        "vehicle": {
            "make": "Honda",
            "model": "Accord EX-L",
            "year": 2021,
            "color": "Lunar Silver Metallic",
            "vin": "1HGCM82633A001234",
            "licensePlate": "OH-HRP-4821"
        },
        "premium": 2400,
        "coverageAmount": 300000,
        "deductible": 500,
        "status": "Active",
        "startDate": "2025-03-01",
        "endDate": "2026-03-01",
        "claimHistory": [
            {"claimId": "CLM-5001", "date": "2025-09-15", "type": "Minor Fender Bender", "amount": 3200, "status": "Settled"}
        ],
        "addOns": ["Roadside Assistance", "Rental Reimbursement"]
    },
    "CAR-100002": {
        "policyId": "CAR-100002",
        "name": "Sarah Jenkins",
        "age": 29,
        "phone": "(555) 014-9921",
        "email": "sarah.jenkins@email.com",
        "policyType": "Car Insurance — Third Party",
        "coverageType": "Third Party Only",
        "vehicle": {
            "make": "Toyota",
            "model": "RAV4 LE",
            "year": 2018,
            "color": "Midnight Blue",
            "vin": "2T1BR32E91C123456",
            "licensePlate": "WA-SJK-7733"
        },
        "premium": 1200,
        "coverageAmount": 100000,
        "deductible": 1000,
        "status": "Active",
        "startDate": "2025-06-15",
        "endDate": "2026-06-15",
        "claimHistory": [],
        "addOns": []
    },
    "CAR-100003": {
        "policyId": "CAR-100003",
        "name": "David Alvez",
        "age": 54,
        "phone": "(555) 017-4433",
        "email": "david.alvez@email.com",
        "policyType": "Car Insurance — Comprehensive",
        "coverageType": "Comprehensive + Collision",
        "vehicle": {
            "make": "Ford",
            "model": "F-150 Lariat",
            "year": 2023,
            "color": "Agate Black",
            "vin": "1FTFW1E88PK192837",
            "licensePlate": "AZ-DAL-2109"
        },
        "premium": 3600,
        "coverageAmount": 500000,
        "deductible": 250,
        "status": "Active",
        "startDate": "2025-01-10",
        "endDate": "2026-01-10",
        "claimHistory": [
            {"claimId": "CLM-5010", "date": "2025-04-20", "type": "Windshield Replacement", "amount": 850, "status": "Settled"},
            {"claimId": "CLM-5011", "date": "2025-11-05", "type": "Rear-End Collision", "amount": 12500, "status": "Under Review"}
        ],
        "addOns": ["Roadside Assistance", "Zero Depreciation", "Engine Protection", "Passenger Cover", "Rental Reimbursement"]
    },

    # ─── LIFE INSURANCE POLICIES ─── #
    "LIFE-200001": {
        "policyId": "LIFE-200001",
        "name": "Robert J. Whitfield",
        "age": 62,
        "phone": "(555) 022-6891",
        "email": "robert.whitfield@email.com",
        "policyType": "Life Insurance — Term Life",
        "coverageType": "Term Life (20 Year)",
        "coverageAmount": 500000,
        "premium": 4800,
        "status": "Active",
        "startDate": "2015-05-20",
        "endDate": "2035-05-20",
        "beneficiaries": [
            {"name": "Margaret Whitfield", "relationship": "Spouse", "share": "60%"},
            {"name": "James Whitfield", "relationship": "Son", "share": "40%"}
        ],
        "contestabilityExpired": True,
        "medicalHistory": "Non-smoker, no pre-existing conditions at time of policy inception",
        "lastPremiumPaid": "2026-01-20"
    },
    "LIFE-200002": {
        "policyId": "LIFE-200002",
        "name": "Catherine M. Brooks",
        "age": 38,
        "phone": "(555) 033-7742",
        "email": "catherine.brooks@email.com",
        "policyType": "Life Insurance — Whole Life",
        "coverageType": "Whole Life with Cash Value",
        "coverageAmount": 1000000,
        "premium": 9600,
        "cashValue": 42500,
        "status": "Active",
        "startDate": "2020-08-01",
        "endDate": "Lifetime",
        "beneficiaries": [
            {"name": "Daniel Brooks", "relationship": "Spouse", "share": "100%"}
        ],
        "contestabilityExpired": True,
        "medicalHistory": "Non-smoker, mild asthma managed with medication",
        "lastPremiumPaid": "2026-02-01"
    },
    "LIFE-200003": {
        "policyId": "LIFE-200003",
        "name": "Marcus A. Rivera",
        "age": 29,
        "phone": "(555) 044-8853",
        "email": "marcus.rivera@email.com",
        "policyType": "Life Insurance — Accidental Death & Dismemberment",
        "coverageType": "AD&D",
        "coverageAmount": 750000,
        "premium": 1800,
        "status": "Active",
        "startDate": "2025-11-01",
        "endDate": "2026-11-01",
        "beneficiaries": [
            {"name": "Elena Rivera", "relationship": "Spouse", "share": "50%"},
            {"name": "Rosa Rivera", "relationship": "Mother", "share": "50%"}
        ],
        "contestabilityExpired": False,
        "medicalHistory": "Healthy, active lifestyle, no pre-existing conditions",
        "lastPremiumPaid": "2026-02-01"
    },

    # ─── MEDICAL INSURANCE POLICIES ─── #
    "MED-300001": {
        "policyId": "MED-300001",
        "name": "Karen L. Mitchell",
        "age": 42,
        "phone": "(555) 055-3214",
        "email": "karen.mitchell@email.com",
        "policyType": "Medical Insurance — Individual Health",
        "coverageType": "Individual Health (PPO)",
        "coverageAmount": 500000,
        "premium": 6200,
        "status": "Active",
        "startDate": "2025-04-01",
        "endDate": "2026-04-01",
        "networkHospitals": ["Mount Sinai Hospital", "NYU Langone Health", "NewYork-Presbyterian", "Memorial Sloan Kettering"],
        "roomCategory": "Private",
        "copay": 10,
        "deductible": 2500,
        "preExistingWaiting": "Completed — 4-year waiting period expired",
        "maternity": False,
        "dayCareProcedures": True,
        "subLimits": {
            "roomRent": "$1,200/day",
            "icu": "$2,500/day",
            "ambulance": "$500 per trip"
        },
        "claimHistory": [
            {"claimId": "CLM-M-7001", "date": "2025-08-10", "type": "ER Visit — Allergic Reaction", "amount": 4500, "status": "Settled"}
        ],
        "addOns": ["Day-Care Procedures", "Ambulance Cover"]
    },
    "MED-300002": {
        "policyId": "MED-300002",
        "name": "Thomas R. Nguyen",
        "age": 55,
        "phone": "(555) 066-9875",
        "email": "thomas.nguyen@email.com",
        "policyType": "Medical Insurance — Family Plan",
        "coverageType": "Family Plan (HMO)",
        "coverageAmount": 1000000,
        "premium": 14400,
        "status": "Active",
        "startDate": "2025-07-01",
        "endDate": "2026-07-01",
        "networkHospitals": ["Mayo Clinic", "Cleveland Clinic", "Johns Hopkins Hospital", "Massachusetts General Hospital"],
        "roomCategory": "Semi-Private",
        "copay": 20,
        "deductible": 5000,
        "preExistingWaiting": "Active — 2 years remaining (Type 2 Diabetes disclosed)",
        "maternity": True,
        "dayCareProcedures": True,
        "subLimits": {
            "roomRent": "$800/day",
            "icu": "$1,800/day",
            "ambulance": "$400 per trip"
        },
        "claimHistory": [
            {"claimId": "CLM-M-7010", "date": "2025-09-20", "type": "Knee Arthroscopy (Day-Care)", "amount": 8500, "status": "Settled"},
            {"claimId": "CLM-M-7011", "date": "2025-12-05", "type": "Spouse — Appendectomy", "amount": 32000, "status": "Under Review"}
        ],
        "addOns": ["Day-Care Procedures", "Maternity Cover", "Ambulance Cover", "OPD Cover"]
    },
    "MED-300003": {
        "policyId": "MED-300003",
        "name": "Jennifer S. Park",
        "age": 34,
        "phone": "(555) 077-6543",
        "email": "jennifer.park@email.com",
        "policyType": "Medical Insurance — Critical Illness",
        "coverageType": "Critical Illness",
        "coverageAmount": 500000,
        "premium": 3600,
        "status": "Active",
        "startDate": "2025-01-15",
        "endDate": "2026-01-15",
        "networkHospitals": ["MD Anderson Cancer Center", "Memorial Sloan Kettering", "Dana-Farber Cancer Institute"],
        "roomCategory": "Private",
        "copay": 0,
        "deductible": 0,
        "preExistingWaiting": "Completed — no waiting period applicable",
        "maternity": False,
        "dayCareProcedures": False,
        "subLimits": {},
        "coveredConditions": ["Cancer", "Heart Attack", "Stroke", "Kidney Failure", "Major Organ Transplant", "Multiple Sclerosis"],
        "claimHistory": [],
        "addOns": []
    }
}

# Track whether DB is available
_db_available = False


def set_db_available(available: bool):
    """Called at startup to indicate if DB is configured."""
    global _db_available
    _db_available = available


async def get_member(policy_id: str = None, name: str = None, phone: str = None):
    """
    Look up a policyholder by their policy ID or Phone Number.
    Uses PostgreSQL when available, falls back to in-memory dict.
    """
    if _db_available:
        try:
            from db.queries import get_policy, get_policy_by_phone
            if policy_id:
                result = await get_policy(policy_id)
                if result:
                    return result
            if phone:
                result = await get_policy_by_phone(phone)
                if result:
                    return result
            return None
        except Exception as e:
            logger.warning(f"DB lookup failed, falling back to in-memory: {e}")

    # Fallback to in-memory
    return _get_member_sync(policy_id=policy_id, name=name, phone=phone)


def _get_member_sync(policy_id: str = None, name: str = None, phone: str = None):
    """Synchronous in-memory fallback lookup."""
    if policy_id:
        policy_id = policy_id.upper().strip()
        if policy_id in MEMBER_DB:
            return MEMBER_DB[policy_id]

    search_phone = re.sub(r'\D', '', phone) if phone else None
    if search_phone and len(search_phone) >= 10:
        for pid, data in MEMBER_DB.items():
            db_phone = re.sub(r'\D', '', data.get("phone", ""))
            if search_phone in db_phone:
                return data

    return None


def get_all_members() -> list:
    """Returns a list of all member records (in-memory only, for testing)."""
    return list(MEMBER_DB.values())