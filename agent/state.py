from typing import Optional, Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class AgentState(TypedDict):
    """
    State representing the context of a single call session.
    Using `add_messages` to append new chunks into the ReAct loop.
    """
    messages: Annotated[list, add_messages]
    
    # Core call tracking
    transcript: str
    full_transcript: str
    is_finalized: bool
    
    # Extracted or determined state
    intent: Optional[str]
    claim_type: Optional[str]
    
    # External system data
    member_data: Optional[dict]
    accumulated_facts: dict
    
    # Pre-fetched knowledge (injected into prompt to avoid tool call latency)
    knowledge_docs: Optional[list]
    
    # Detected caller languages (BCP-47 tags from Deepgram)
    caller_languages: Optional[list]
