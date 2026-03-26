import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.prompts import generate_system_prompt
from agent.tools import lookup_policyholder, search_knowledge_base, check_compliance_rules

from langchain_openai import ChatOpenAI

# Define our tools array
tools = [lookup_policyholder, search_knowledge_base, check_compliance_rules]

# Lazy singletons — initialized on first use so load_dotenv() has already run
_llm = None
_llm_with_tools = None
_tool_node = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3, streaming=True)
    return _llm

def _get_llm_with_tools():
    global _llm_with_tools
    if _llm_with_tools is None:
        _llm_with_tools = _get_llm().bind_tools(tools)
    return _llm_with_tools

def _get_tool_node():
    global _tool_node
    if _tool_node is None:
        _tool_node = ToolNode(tools)
    return _tool_node


async def call_agent(state: AgentState) -> dict:
    """
    The main reasoning node.
    1. Generates the system prompt context.
    2. Calls the LLM with the bound tools.
    3. Returns the output message.
    """
    # 1. Generate dynamic System Prompt based on current state
    sys_prompt_text = generate_system_prompt(
        intent=state.get("intent"),
        claim_type=state.get("claim_type"),
        member_data=state.get("member_data"),
        collected_facts=state.get("accumulated_facts"),
        full_transcript=state.get("full_transcript"),
        knowledge_docs=state.get("knowledge_docs"),
        compliance_alerts=state.get("compliance_alerts"),
        caller_languages=state.get("caller_languages"),
        stall_response_sent=state.get("stall_response_sent"),
    )
    
    # 2. Build the messages list (System + Conversation History)
    # The `state["messages"]` will hold the ongoing ReAct loop messages (Human -> AI (tool_calls) -> Tool -> AI)
    # For the *call center* perspective, the transcript is provided via the `transcript` flat string 
    # and we inject it as the latest HumanMessage ONLY on the first step in the ReAct loop.
    # On subsequent iterations, the tool-call trace in state["messages"] already contains the context,
    # and the full transcript is available in the system prompt.
    
    messages = [SystemMessage(content=sys_prompt_text)]
    
    if state.get("messages"):
        # Subsequent ReAct iteration: state["messages"] contains [AI(tool_calls), Tool(...)]
        # The transcript context is already in the system prompt via full_transcript.
        # Prepend the original HumanMessage so message ordering is valid,
        # then append the tool-call trace.
        messages.append(HumanMessage(content=state["transcript"]))
        messages.extend(state["messages"])
    else:
        # First iteration: inject the current utterance as HumanMessage
        messages.append(HumanMessage(content=state["transcript"]))

    # 3. Call the LLM
    # In LangGraph streaming, astream_events will hook into this call because `llm_with_tools` is a Runnable.
    response = await _get_llm_with_tools().ainvoke(messages)
    
    # 4. Return as append operation to state
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """
    Determine whether to route to tools or end the sequence.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM made a tool call, route to tools
    if last_message.tool_calls:
        return "tools"
        
    # Otherwise, we're done generating the response
    return "END"
