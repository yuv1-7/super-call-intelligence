import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.prompts import generate_system_prompt
from agent.tools import lookup_policyholder, search_knowledge_base, check_compliance_rules

# Initialize the OpenAI Client for the ChatModel (bound to tools)
# We are using ChatOpenAI from langchain-openai here to bind native tools properly
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.3, streaming=True)

# Define our tools array
tools = [lookup_policyholder, search_knowledge_base, check_compliance_rules]

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(tools)

# Create the standard prebuilt ToolNode
tool_node = ToolNode(tools)


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
        full_transcript=state.get("full_transcript")
    )
    
    # 2. Build the messages list (System + Conversation History)
    # The `state["messages"]` will hold the ongoing ReAct loop messages (Human -> AI (tool_calls) -> Tool -> AI)
    # But for the *call center* perspective, the transcript is provided via the `transcript` flat string 
    # and we just inject it as the latest HumanMessage if it's the first step in the ReAct loop.
    
    messages = [SystemMessage(content=sys_prompt_text)]
    
    # The transcript is the current user's input for this turn.
    # We must always include it before the tool-call trace if we are mid-loop.
    messages.append(HumanMessage(content=state["transcript"]))
    
    # Append the ongoing ReAct loop messages (tool calls & results) if they exist.
    if state.get("messages"):
        messages.extend(state["messages"])
    # 3. Call the LLM
    # In LangGraph streaming, astream_events will hook into this call because `llm_with_tools` is a Runnable.
    response = await llm_with_tools.ainvoke(messages)
    
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
