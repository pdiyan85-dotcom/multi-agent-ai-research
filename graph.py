# graph.py
"""LangGraph workflow definition for Multi-Agent AI Research Assistant."""

from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
import operator

from agents import (
    create_supervisor_chain,
    create_researcher_agent,
    create_writer_chain,
    create_critique_chain
)

# --- 1. Define Research Workflow State ---

class ResearchState(TypedDict):
    """State schema for the multi-agent research graph."""
    main_task: str
    research_findings: Annotated[List[str], operator.add]
    draft: str
    critique_notes: str
    revision_number: int
    next_step: str
    current_sub_task: str

# --- 2. Initialize Agent Chains ---

supervisor_chain = create_supervisor_chain()
researcher_agent = create_researcher_agent()
writer_chain = create_writer_chain()
critique_chain = create_critique_chain()

# --- 3. Define Graph Node Functions ---

def supervisor_node(state: ResearchState) -> dict:
    """Supervisor node: analyzes progress and determines next task/agent."""
    print("\n=== [AGENT] SUPERVISOR ===")
    decision = supervisor_chain(state)
    next_step = decision.get("next_step", "researcher")
    task_desc = decision.get("task_description", "Continue research workflow")
    
    print(f"Supervisor Decision: {next_step}")
    print(f"Task Instruction: {task_desc}")
    
    return {
        "next_step": next_step,
        "current_sub_task": task_desc,
    }

def research_node(state: ResearchState) -> dict:
    """Researcher node: executes live search for topic data."""
    print("\n=== [AGENT] RESEARCHER ===")
    sub_task = state.get("current_sub_task", state.get("main_task"))
    print(f"Target Query: {sub_task}")
    
    try:
        result = researcher_agent({"input": sub_task})
        findings = result.get("output", "Research query executed.")
        print(f"Research Findings length: {len(findings)} chars")
    except Exception as e:
        print(f"Research node error: {e}")
        findings = f"Research notes collected for topic: {sub_task}"
    
    return {
        "research_findings": [findings]
    }

def write_node(state: ResearchState) -> dict:
    """Writer node: synthesizes findings into structured Markdown report."""
    print("\n=== [AGENT] WRITER ===")
    draft = writer_chain(state)
    current_rev = state.get("revision_number", 0) + 1
    print(f"Draft (Rev {current_rev}) generated: {len(draft)} chars")
    
    return {
        "draft": draft,
        "revision_number": current_rev
    }

def critique_node(state: ResearchState) -> dict:
    """Critique node: performs quality assurance review on draft."""
    print("\n=== [AGENT] CRITIQUER ===")
    critique = critique_chain(state)
    print(f"Critique Evaluation: {critique[:120]}...")
    
    is_approved = "APPROVED" in critique.upper()
    
    if is_approved:
        print("Status: Draft APPROVED by reviewer.")
        return {
            "critique_notes": "APPROVED",
            "next_step": "END"
        }
    else:
        print("Status: Revision requested by reviewer.")
        return {
            "critique_notes": critique,
            "next_step": "writer"
        }

# --- 4. Build LangGraph Workflow ---

def build_graph():
    """Constructs and compiles the multi-agent StateGraph."""
    workflow = StateGraph(ResearchState)
    
    # Add Agent Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("writer", write_node)
    workflow.add_node("critiquer", critique_node)
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Define Core Edges
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("writer", "critiquer")
    workflow.add_edge("critiquer", "supervisor")
    
    # Conditional Edges from Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next_step", "researcher"),
        {
            "researcher": "researcher",
            "writer": "writer",
            "END": END
        }
    )
    
    return workflow.compile()

# Expose compiled app
app = build_graph()
