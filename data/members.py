# Mock CRM Database for National Sentinel Insurance
# This simulates the data normally pulled from the ClaimSphere Policy Administration System

MOCK_MEMBER_DATABASE = {
    "(555) 019-8372": {
        "name": "Michael T. Henderson",
        "policy_number": "NS-88402911",
        "dob": "08/14/1982",
        "phone": "(555) 019-8372",
        "address": "1492 Elm Street, Apt 4B, Columbus, OH 43215",
        "vehicle": "2021 Honda Accord EX-L",
        "vin": "1HGCM82633A001234",
        "policy_status": "ACTIVE",
        "coverage_limits": {
            "bodily_injury": "$100,000 / $300,000",
            "property_damage": "$100,000",
            "collision_deductible": "$500",
            "comprehensive_deductible": "$250"
        },
        "add_ons": [
            "RR-01 (Rental Reimbursement)", 
            "RA-01 (Roadside Assistance)"
        ]
    },
    "(555) 014-9921": {
        "name": "Sarah Jenkins",
        "policy_number": "NS-99381022",
        "dob": "11/02/1995",
        "phone": "(555) 014-9921",
        "address": "800 Westlake Ave N, Seattle, WA 98109",
        "vehicle": "2018 Toyota RAV4 LE",
        "vin": "2T1BR32E91C123456",
        "policy_status": "ACTIVE",
        "coverage_limits": {
            "bodily_injury": "$50,000 / $100,000",
            "property_damage": "$50,000",
            "collision_deductible": "$1,000",
            "comprehensive_deductible": "$1,000"
        },
        "add_ons": [
            "RS-02 (Rideshare / TNC Endorsement)"
        ]
    },
    "(555) 017-4433": {
        "name": "David Alvez",
        "policy_number": "NS-77299104",
        "dob": "03/25/1970",
        "phone": "(555) 017-4433",
        "address": "12109 Desert Springs Blvd, Scottsdale, AZ 85260",
        "vehicle": "2023 Ford F-150 Lariat",
        "vin": "1FTFW1E88PK192837",
        "policy_status": "ACTIVE",
        "coverage_limits": {
            "bodily_injury": "$250,000 / $500,000",
            "property_damage": "$100,000",
            "collision_deductible": "$250",
            "comprehensive_deductible": "$0 (Full Glass Coverage)"
        },
        "add_ons": [
            "RR-01 (Rental Reimbursement)", 
            "RA-01 (Roadside Assistance)"
        ]
    }
}

def get_member_by_phone(phone_number: str) -> dict:
    """
    Simulates a ClaimSphere CRM lookup using the caller's phone number.
    Returns the member profile dictionary if found, else None.
    """
    # Simple normalization to handle potential input variations
    normalized_input = phone_number.strip()
    return MOCK_MEMBER_DATABASE.get(normalized_input)

def get_member_by_policy(policy_number: str) -> dict:
    """
    Simulates a ClaimSphere CRM lookup using the National Sentinel policy number.
    Returns the member profile dictionary if found, else None.
    """
    normalized_policy = policy_number.strip().upper()
    for member in MOCK_MEMBER_DATABASE.values():
        if member["policy_number"] == normalized_policy:
            return member
    return None

def get_all_members() -> list:
    """
    Returns a list of all member records for testing/UI purposes.
    """
    return list(MOCK_MEMBER_DATABASE.values())