import json
from langchain_core.tools import tool
from typing import Optional

from data.members import get_member
from data.knowledge import search_knowledge, get_compliance_alerts

@tool
async def lookup_policyholder(policy_id: Optional[str] = None, phone: Optional[str] = None) -> str:
    """
    Look up a policyholder's insurance account details by their Policy ID (e.g. NS-88402911) 
    or their phone number. Only provide ONE of the arguments if possible.
    """
    if not policy_id and not phone:
        return json.dumps({"error": "Must provide either policy_id or phone"})
        
    member = await get_member(policy_id=policy_id, phone=phone)
    if not member:
        # Give LLM a clean response to parse naturally so it doesn't hallucinate
        return json.dumps({"status": "Failed", "message": f"No account found for given details (policy_id: {policy_id}, phone: {phone})"})
        
    # Return as JSON string for the LLM to process
    return json.dumps(member)


@tool
def search_knowledge_base(query: str, category: Optional[str] = None, insurance_type: Optional[str] = None) -> str:
    """
    Search the insurance knowledge base for procedures, timelines, required documents, 
    and coverage rules based on a user's intent or questions.
    Args:
        query: The search keywords to match against (e.g. "car accident towing").
        category: Optional category filter. E.g. "car_insurance", "life_insurance".
        insurance_type: Optional insurance domain filter. E.g. "car_insurance", "life_insurance", "medical_insurance".
                       This filters results to only the relevant insurance type to avoid cross-domain contamination.
    """
    docs = search_knowledge(query, claim_type=insurance_type or category, category=category)
    if not docs:
        return json.dumps({"results": []})
    
    return json.dumps({"results": docs})


@tool
def check_compliance_rules(intent: str, transcript: str) -> str:
    """
    Check for active compliance and regulatory alerts that MUST be communicated to the 
    caller based on the ongoing claim intent and discussed context.
    Args:
        intent: The current detected intent of the call (e.g. "car_accident").
        transcript: The text segment of the call to check for triggers.
    """
    alerts = get_compliance_alerts(intent=intent, transcript=transcript)
    if not alerts:
        return json.dumps({"alerts": []})
        
    return json.dumps({"alerts": alerts})
