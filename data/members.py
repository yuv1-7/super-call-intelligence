# data/members.py — Mock CRM for Insurance Policyholders

MEMBER_DB = {
    # ─── CAR INSURANCE POLICIES ─── #
    "CAR-100001": {
        "policyId": "CAR-100001",
        "name": "Rajesh Kumar",
        "age": 35,
        "phone": "+91 98765-43210",
        "email": "rajesh.kumar@email.com",
        "policyType": "Car Insurance – Comprehensive",
        "coverageType": "Comprehensive",
        "vehicle": {
            "make": "Hyundai",
            "model": "Creta",
            "year": 2023,
            "color": "Pearl White",
            "vin": "MALC381CDNM123456",
            "licensePlate": "DL-01-AB-1234"
        },
        "premium": 18500,
        "coverageAmount": 1200000,
        "deductible": 15000,
        "status": "Active",
        "startDate": "2025-03-01",
        "endDate": "2026-03-01",
        "claimHistory": [
            {"claimId": "CLM-5001", "date": "2025-09-15", "type": "Minor Scratch", "amount": 8500, "status": "Settled"}
        ],
        "addOns": ["Roadside Assistance", "Zero Depreciation", "Engine Protection"]
    },
    "CAR-100002": {
        "policyId": "CAR-100002",
        "name": "Priya Sharma",
        "age": 28,
        "phone": "+91 87654-32109",
        "email": "priya.sharma@email.com",
        "policyType": "Car Insurance – Third Party",
        "coverageType": "Third Party Only",
        "vehicle": {
            "make": "Maruti Suzuki",
            "model": "Swift",
            "year": 2022,
            "color": "Midnight Blue",
            "vin": "MA3FJEB1S00234567",
            "licensePlate": "MH-02-CD-5678"
        },
        "premium": 6200,
        "coverageAmount": 750000,
        "deductible": 0,
        "status": "Active",
        "startDate": "2025-06-15",
        "endDate": "2026-06-15",
        "claimHistory": [],
        "addOns": []
    },
    "CAR-100003": {
        "policyId": "CAR-100003",
        "name": "Amit Patel",
        "age": 45,
        "phone": "+91 76543-21098",
        "email": "amit.patel@email.com",
        "policyType": "Car Insurance – Comprehensive",
        "coverageType": "Comprehensive + Collision",
        "vehicle": {
            "make": "Toyota",
            "model": "Fortuner",
            "year": 2024,
            "color": "Phantom Brown",
            "vin": "MBJB3CF1JPT345678",
            "licensePlate": "GJ-05-EF-9012"
        },
        "premium": 42000,
        "coverageAmount": 3500000,
        "deductible": 25000,
        "status": "Active",
        "startDate": "2025-01-10",
        "endDate": "2026-01-10",
        "claimHistory": [
            {"claimId": "CLM-5010", "date": "2025-04-20", "type": "Windshield Replacement", "amount": 22000, "status": "Settled"},
            {"claimId": "CLM-5011", "date": "2025-11-05", "type": "Rear-End Collision", "amount": 185000, "status": "Under Review"}
        ],
        "addOns": ["Roadside Assistance", "Zero Depreciation", "Engine Protection", "Passenger Cover", "Rental Reimbursement"]
    },

    # ─── LIFE INSURANCE POLICIES ─── #
    "LIFE-200001": {
        "policyId": "LIFE-200001",
        "name": "Suresh Menon",
        "age": 62,
        "phone": "+91 65432-10987",
        "email": "suresh.menon@email.com",
        "policyType": "Life Insurance – Term Life",
        "coverageType": "Term Life (20 Year)",
        "coverageAmount": 5000000,
        "premium": 28000,
        "status": "Active",
        "startDate": "2015-05-20",
        "endDate": "2035-05-20",
        "beneficiaries": [
            {"name": "Lakshmi Menon", "relationship": "Spouse", "share": "60%"},
            {"name": "Anand Menon", "relationship": "Son", "share": "40%"}
        ],
        "contestabilityExpired": True,
        "medicalHistory": "Non-smoker, no pre-existing conditions at time of policy inception",
        "lastPremiumPaid": "2026-01-20"
    },
    "LIFE-200002": {
        "policyId": "LIFE-200002",
        "name": "Meera Iyer",
        "age": 38,
        "phone": "+91 54321-09876",
        "email": "meera.iyer@email.com",
        "policyType": "Life Insurance – Whole Life",
        "coverageType": "Whole Life with Cash Value",
        "coverageAmount": 10000000,
        "premium": 65000,
        "cashValue": 425000,
        "status": "Active",
        "startDate": "2020-08-01",
        "endDate": "Lifetime",
        "beneficiaries": [
            {"name": "Arjun Iyer", "relationship": "Spouse", "share": "100%"}
        ],
        "contestabilityExpired": True,
        "medicalHistory": "Non-smoker, mild asthma managed with medication",
        "lastPremiumPaid": "2026-02-01"
    },
    "LIFE-200003": {
        "policyId": "LIFE-200003",
        "name": "Vikram Singh",
        "age": 29,
        "phone": "+91 43210-98765",
        "email": "vikram.singh@email.com",
        "policyType": "Life Insurance – Accidental Death & Dismemberment",
        "coverageType": "AD&D",
        "coverageAmount": 7500000,
        "premium": 12000,
        "status": "Active",
        "startDate": "2025-11-01",
        "endDate": "2026-11-01",
        "beneficiaries": [
            {"name": "Neha Singh", "relationship": "Spouse", "share": "50%"},
            {"name": "Kavita Singh", "relationship": "Mother", "share": "50%"}
        ],
        "contestabilityExpired": False,
        "medicalHistory": "Healthy, active lifestyle, no pre-existing conditions",
        "lastPremiumPaid": "2026-02-01"
    },

    # ─── MEDICAL INSURANCE POLICIES ─── #
    "MED-300001": {
        "policyId": "MED-300001",
        "name": "Kavita Reddy",
        "age": 42,
        "phone": "+91 32109-87654",
        "email": "kavita.reddy@email.com",
        "policyType": "Medical Insurance – Individual Health",
        "coverageType": "Individual Health",
        "coverageAmount": 1000000,
        "premium": 15000,
        "status": "Active",
        "startDate": "2025-04-01",
        "endDate": "2026-04-01",
        "networkHospitals": ["Apollo Hospital", "Fortis Hospital", "Max Super Speciality Hospital", "AIIMS"],
        "roomCategory": "Private",
        "copay": 10,
        "deductible": 5000,
        "preExistingWaiting": "Completed — 4-year waiting period expired",
        "maternity": False,
        "dayCareProcedures": True,
        "subLimits": {
            "roomRent": "₹8,000/day",
            "icu": "₹15,000/day",
            "ambulance": "₹3,000 per trip"
        },
        "claimHistory": [
            {"claimId": "CLM-M-7001", "date": "2025-08-10", "type": "Dengue Hospitalization", "amount": 45000, "status": "Settled"}
        ],
        "addOns": ["Day-Care Procedures", "Ambulance Cover"]
    },
    "MED-300002": {
        "policyId": "MED-300002",
        "name": "Rohit Deshmukh",
        "age": 55,
        "phone": "+91 21098-76543",
        "email": "rohit.deshmukh@email.com",
        "policyType": "Medical Insurance – Family Floater",
        "coverageType": "Family Floater",
        "coverageAmount": 2500000,
        "premium": 32000,
        "status": "Active",
        "startDate": "2025-07-01",
        "endDate": "2026-07-01",
        "networkHospitals": ["Medanta Hospital", "Narayana Health", "Manipal Hospital", "Columbia Asia"],
        "roomCategory": "Semi-Private",
        "copay": 20,
        "deductible": 10000,
        "preExistingWaiting": "Active — 2 years remaining (Type 2 Diabetes disclosed)",
        "maternity": True,
        "dayCareProcedures": True,
        "subLimits": {
            "roomRent": "₹5,000/day",
            "icu": "₹10,000/day",
            "ambulance": "₹2,500 per trip"
        },
        "claimHistory": [
            {"claimId": "CLM-M-7010", "date": "2025-09-20", "type": "Knee Arthroscopy (Day-Care)", "amount": 75000, "status": "Settled"},
            {"claimId": "CLM-M-7011", "date": "2025-12-05", "type": "Wife — Appendectomy", "amount": 120000, "status": "Under Review"}
        ],
        "addOns": ["Day-Care Procedures", "Maternity Cover", "Ambulance Cover", "OPD Cover"]
    },
    "MED-300003": {
        "policyId": "MED-300003",
        "name": "Sneha Kapoor",
        "age": 34,
        "phone": "+91 10987-65432",
        "email": "sneha.kapoor@email.com",
        "policyType": "Medical Insurance – Critical Illness",
        "coverageType": "Critical Illness",
        "coverageAmount": 5000000,
        "premium": 18000,
        "status": "Active",
        "startDate": "2025-01-15",
        "endDate": "2026-01-15",
        "networkHospitals": ["Tata Memorial Hospital", "Rajiv Gandhi Cancer Institute", "Kokilaben Hospital"],
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


import re

def get_member(policy_id: str = None, name: str = None, phone: str = None):
    """
    Look up a policyholder by their policy ID or Phone Number.
    Strips formatting on phones for matching. Name is kept in signature for compatibility but ignored for searching.
    """
    # 1. Direct ID match
    if policy_id:
        policy_id = policy_id.upper().strip()
        if policy_id in MEMBER_DB:
            return MEMBER_DB[policy_id]
            
    # Normalize input phone
    search_phone = re.sub(r'\D', '', phone) if phone else None

    # 2. Iterate through all members to find a match for phone
    # Require at least 10 digits to avoid false positives from partial numbers
    # (e.g., speech recognition splitting "8765432109" across two utterances)
    if search_phone and len(search_phone) >= 10:
        for pid, data in MEMBER_DB.items():
            db_phone = re.sub(r'\D', '', data.get("phone", ""))
            if search_phone in db_phone:
                return data

    return None
