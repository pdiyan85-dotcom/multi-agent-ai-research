# app.py
"""Streamlit Web Application for Multi-Agent AI Research Assistant."""

import os
import time
import streamlit as st
from dotenv import load_dotenv
from graph import app

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Multi-Agent AI Research Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .agent-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 10px;
    }
    .stMetric {
        background-color: #f0f4f8;
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- API Keys Check ---
def check_api_keys():
    """Verify that required API credentials are available."""
    together_key = os.environ.get("TOGETHER_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")
    
    missing = []
    if not together_key:
        missing.append("TOGETHER_API_KEY")
    if not tavily_key:
        missing.append("TAVILY_API_KEY")
        
    if missing:
        st.error(f"🚨 Missing API key(s): `{', '.join(missing)}`. Please set them in your `.env` file.")
        return False
    return True

# --- Header & Intro ---
st.markdown('<div class="main-header">Multi-Agent AI Research Assistant 🤖🧠</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">An autonomous team of specialized AI agents collaborating via LangGraph to research, compose, and review technical reports.</div>', unsafe_allow_html=True)

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Workflow Configuration")
    
    max_iterations = st.slider(
        "Max Workflow Recursion Limit",
        min_value=5,
        max_value=30,
        value=15,
        help="Maximum recursion depth for LangGraph execution loops"
    )
    
    st.divider()
    st.subheader("🔑 Credentials Status")
    if check_api_keys():
        st.success("✅ `TOGETHER_API_KEY` active")
        st.success("✅ `TAVILY_API_KEY` active")
    
    st.divider()
    st.subheader("👥 Agent Team Architecture")
    st.markdown("""
    - 🎯 **Supervisor**: Graph controller orchestrating agent routing
    - 🔍 **Researcher**: Fetches web search results via Tavily
    - ✍️ **Writer**: Composes report drafts using Mixtral-8x7B
    - 🔎 **Critiquer**: Reviews drafts for completeness & rigor
    """)

# --- Main Interface ---
st.header("🚀 Initiate Research Task")

topic = st.text_input(
    "Enter your research topic or question:",
    placeholder="e.g., Breakthroughs in Quantum Error Correction and commercial viability",
    key="topic_input"
)

if st.button("🚀 Start Autonomous Research", type="primary", use_container_width=True):
    if not check_api_keys():
        st.stop()
    if not topic.strip():
        st.warning("⚠️ Please provide a research topic before starting.")
    else:
        initial_state = {
            "main_task": topic,
            "research_findings": [],
            "draft": "",
            "critique_notes": "",
            "revision_number": 0,
            "next_step": "",
            "current_sub_task": ""
        }
        
        config = {"recursion_limit": max_iterations}
        
        st.info("🤖 Agents deployed! Initiating real-time state execution...")
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        progress_container = st.container()
        final_state = None
        step_count = 0
        all_states = []
        
        try:
            with progress_container:
                st.subheader("🔄 Real-Time Agent Execution Log")
                
                for step in app.stream(initial_state, config=config):
                    step_count += 1
                    progress_bar.progress(min(step_count / max_iterations, 1.0))
                    
                    node_name = list(step.keys())[0]
                    node_output = step[node_name]
                    
                    all_states.append((node_name, node_output))
                    final_state = node_output
                    
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"#### 🤖 Agent Node: `{node_name.upper()}`")
                        with col2:
                            st.caption(f"Execution Step #{step_count}")
                        
                        if node_name == "supervisor":
                            next_step = node_output.get('next_step', 'N/A')
                            task = node_output.get('current_sub_task', 'N/A')
                            st.markdown(f"**Decision:** Task assigned to `{next_step}`")
                            st.markdown(f"**Instruction:** {task}")
                            
                        elif node_name == "researcher":
                            findings = node_output.get('research_findings', [])
                            if findings:
                                latest = findings[-1]
                                st.success("✓ Live search completed & summarized")
                                if len(latest) > 300:
                                    st.info(latest[:300] + "...")
                                    with st.expander(f"📖 Full Research Data (Step {step_count})"):
                                        st.markdown(latest)
                                else:
                                    st.info(latest)
                                    
                        elif node_name == "writer":
                            draft = node_output.get('draft', '')
                            revision = node_output.get('revision_number', 0)
                            st.success(f"✓ Report Revision #{revision} composed ({len(draft)} chars)")
                            if len(draft) > 400:
                                st.info(draft[:400] + "...")
                                with st.expander(f"📖 View Draft Revision #{revision}"):
                                    st.markdown(draft)
                            else:
                                st.info(draft)
                                
                        elif node_name == "critiquer":
                            critique = node_output.get('critique_notes', '')
                            if "APPROVED" in critique.upper():
                                st.success("✅ Peer Review: Draft APPROVED!")
                            else:
                                st.warning("📝 Peer Review: Revisions Requested")
                            
                            if len(critique) > 300:
                                st.info(critique[:300] + "...")
                                with st.expander(f"📖 Critique Notes (Step {step_count})"):
                                    st.markdown(critique)
                            else:
                                st.info(critique)
                        
                        st.divider()
                    time.sleep(0.2)
            
            status_placeholder.success("✅ Multi-Agent Workflow Completed Successfully!")
            progress_bar.progress(1.0)
            
        except Exception as e:
            status_placeholder.error("❌ Workflow Execution Stopped")
            st.error(f"An unexpected error occurred during execution: {str(e)}")
            st.exception(e)
        
        # --- Final Report Display ---
        st.divider()
        final_draft = None
        if final_state and isinstance(final_state, dict):
            final_draft = final_state.get("draft", "")
        
        if not final_draft or len(final_draft.strip()) < 50:
            for node_name, state in reversed(all_states):
                if isinstance(state, dict) and state.get("draft"):
                    cand = state.get("draft", "")
                    if len(cand.strip()) > 50:
                        final_draft = cand
                        final_state = state
                        break
        
        if final_draft and len(final_draft.strip()) > 50:
            st.header("📄 Final Autonomous Research Report")
            
            with st.container():
                st.markdown(final_draft)
            
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Execution Metrics")
                rev_count = final_state.get("revision_number", 0) if isinstance(final_state, dict) else 0
                sources_count = len(final_state.get("research_findings", [])) if isinstance(final_state, dict) else 0
                word_count = len(final_draft.split())
                
                m1, m2 = st.columns(2)
                m1.metric("Revisions Passed", rev_count)
                m2.metric("Research Batches", sources_count)
                m3, m4 = st.columns(2)
                m3.metric("Word Count", word_count)
                m4.metric("Character Count", len(final_draft))
                
            with col2:
                st.subheader("🔍 Gathered Evidence & Sources")
                if isinstance(final_state, dict) and final_state.get("research_findings"):
                    with st.expander("Expand all collected research findings", expanded=False):
                        for idx, finding in enumerate(final_state.get("research_findings", []), 1):
                            st.markdown(f"**Finding Batch #{idx}:**")
                            st.write(finding)
                            st.divider()
                else:
                    st.info("No raw research findings available.")
            
            st.download_button(
                label="📥 Download Research Report (.md)",
                data=final_draft,
                file_name=f"research_report_{topic.lower().replace(' ', '_')[:30]}.md",
                mime="text/markdown",
                use_container_width=True
            )
        else:
            st.error("❌ Unable to retrieve final report draft.")

# --- Footer ---
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>Powered by LangGraph, LangChain, Together AI (Mixtral-8x7B) & Tavily Search API</small>
</div>
""", unsafe_allow_html=True)
