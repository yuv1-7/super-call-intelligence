# graph/graph.py — LangGraph state machine for FNOL processing

from langgraph.graph import StateGraph, START, END
from graph.state import AgentState
from graph.nodes import (
    intent_node,
    entity_node,
    member_node,
    knowledge_node,
    compliance_node,
)


def build_graph():
    """
    Build the LangGraph processing pipeline.

    Flow (Parallel):
        START ──┬──> intent ──┬──> compliance ──> END
                │             └──> knowledge ───> END
                └──> entity ──────> member ─────> END
    """
    builder = StateGraph(AgentState)

    # Register all nodes
    builder.add_node("intent", intent_node)
    builder.add_node("entity", entity_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("member", member_node)

    # Branch out concurrently from START
    builder.add_edge(START, "intent")
    builder.add_edge(START, "entity")

    # Sequential dependencies
    builder.add_edge("intent", "knowledge")     # knowledge needs claim_type from intent
    builder.add_edge("intent", "compliance")
    builder.add_edge("entity", "member")

    # All branches must hit END
    builder.add_edge("compliance", END)
    builder.add_edge("member", END)
    builder.add_edge("knowledge", END)

    return builder.compile()
