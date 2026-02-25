# data/knowledge.py — Knowledge & Compliance search (JSON-backed, no VectorDB)

import json
import os

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Load JSON files once at import time ─── #
with open(os.path.join(_DATA_DIR, "knowledge_base.json"), "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE: list[dict] = json.load(f)

with open(os.path.join(_DATA_DIR, "compliance_rules.json"), "r", encoding="utf-8") as f:
    COMPLIANCE_RULES: list[dict] = json.load(f)


def search_knowledge(query: str, category: str | None = None, top_k: int = 2) -> list[dict]:
    """
    Simple keyword-match search over the knowledge base.
    Scores each doc by how many of its tags appear in the query.
    Filters by category (e.g. 'car_insurance', 'life_insurance') when provided.
    Returns the top-k results sorted by relevance.
    """
    query_lower = query.lower()
    scored: list[tuple[int, dict]] = []

    for doc in KNOWLEDGE_BASE:
        # Filter by category if provided — skip docs from wrong category
        doc_cat = doc.get("category", "")
        if category and doc_cat != "general" and doc_cat != category:
            continue

        score = sum(1 for tag in doc["tags"] if tag in query_lower)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def get_compliance_alerts(intent: str, transcript: str) -> list[dict]:
    """
    Match compliance rules based on the detected intent and transcript keywords.
    Rules with trigger '_always' are included for every call.
    Filters rules cleanly so Life rules don't fire on Car calls, etc.
    """
    transcript_lower = transcript.lower()
    intent_category = intent.lower() if intent else ""
    matched: list[dict] = []

    for rule in COMPLIANCE_RULES:
        rule_category = rule.get("category", "")
        # Enforce strict category checks. Only process if 'general' or matches the active intent type.
        if rule_category != "general" and not (rule_category in intent_category or intent_category in rule_category):
            continue

        # Always-on rules
        if "_always" in rule["triggers"]:
            matched.append(rule)
            continue
            
        # Check if any trigger keyword appears in the transcript or intent
        for trigger in rule["triggers"]:
            if trigger in transcript_lower or trigger in intent_category:
                matched.append(rule)
                break

    return matched
