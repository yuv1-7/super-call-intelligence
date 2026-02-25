# graph/nodes.py — LangGraph node functions for Insurance FNOL

import re
from data.members import get_member
from data.knowledge import search_knowledge, get_compliance_alerts
from tools.llm import classify_intent, generate_agent_suggestion, extract_entities


# ─────────────── INTENT NODE ─────────────── #

async def intent_node(state: dict) -> dict:
    """
    Classify the caller's intent using the LLM.
    Returns intent and claim_type.
    """
    result = await classify_intent(state["transcript"])
    return {
        "intent": result.get("intent", "general_inquiry"),
        "claim_type": result.get("claim_type", "general"),
    }


# ─────────────── ENTITY NODE ─────────────── #

async def entity_node(state: dict) -> dict:
    """
    Extract policy IDs, names, and phones from the transcript using LLM.
    """
    text = state["transcript"]
    entities = await extract_entities(text)

    # Clean up empty entities to keep state clean
    cleaned_entities = {k: v for k, v in entities.items() if v is not None}

    return {"entities": cleaned_entities}


# ─────────────── MEMBER NODE ─────────────── #

async def member_node(state: dict) -> dict:
    """
    Fetch policyholder details from mock CRM using extracted entities.
    """
    entities = state.get("entities") or {}
    
    # Preserve member data if it was already fetched (e.g., by fast-path regex)
    member = state.get("member_data")

    # Only fetch from CRM if we haven't found the member yet
    if not member and entities:
        member = get_member(
            policy_id=entities.get("policy_id"),
            name=entities.get("name"),
            phone=entities.get("phone")
        )

    return {"member_data": member}


# ─────────────── KNOWLEDGE NODE ─────────────── #

async def knowledge_node(state: dict) -> dict:
    """
    Retrieve relevant knowledge articles based on the full transcript and claim type.
    """
    # Use full transcript for better keyword matching, fall back to current utterance
    query = state.get("full_transcript") or state["transcript"]
    category = state.get("claim_type")
    docs = search_knowledge(query, category=category)
    return {"knowledge_docs": docs}


# ─────────────── COMPLIANCE NODE ─────────────── #

async def compliance_node(state: dict) -> dict:
    """
    Match compliance rules based on the detected claim type and transcript.
    """
    claim_type = state.get("claim_type") or state.get("intent") or ""
    alerts = get_compliance_alerts(claim_type, state["transcript"])
    return {"compliance_alerts": alerts}
