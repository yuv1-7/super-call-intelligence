from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.nodes import call_agent, tool_node, should_continue

def build_graph():
    """
    Build the LangGraph processing pipeline.
    
    Architecture:
    START -> agent
    agent -> tools (if tool_call) -> agent
    agent -> END (if text response)
    """
    builder = StateGraph(AgentState)
    
    # Add Nodes
    builder.add_node("agent", call_agent)
    builder.add_node("tools", tool_node)
    
    # Define Edges
    builder.add_edge(START, "agent")
    
    # Conditional edge from agent: either hit a tool or resolve to END
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "END": END
        }
    )
    
    # Tools always loop back to agent to evaluate the result
    builder.add_edge("tools", "agent")
    
    return builder.compile()
