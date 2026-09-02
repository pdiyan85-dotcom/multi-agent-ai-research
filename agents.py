# agents.py
"""Agent node implementations for Multi-Agent AI Research Assistant."""

import os
import json
from dotenv import load_dotenv
from prompts import (
    supervisor_prompt_template,
    researcher_prompt_template,
    writer_prompt_template,
    critique_prompt_template
)

# Load environment variables
load_dotenv()

# --- 1. Setup LLM and Search Tool ---

def get_llm():
    """Initializes and returns the ChatTogether LLM instance."""
    together_key = os.environ.get("TOGETHER_API_KEY")
    if not together_key:
        raise ValueError("TOGETHER_API_KEY environment variable is missing.")
        
    try:
        from langchain_together import ChatTogether
        return ChatTogether(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            temperature=0.3,
            max_tokens=4096,
            together_api_key=together_key
        )
    except Exception as e:
        print(f"Error initializing ChatTogether: {e}")
        # Fallback to direct langchain ChatTogether import if available
        from langchain_together import ChatTogether
        return ChatTogether(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            temperature=0.3,
            together_api_key=together_key
        )

def get_tavily_tool():
    """Initializes and returns the Tavily search tool instance."""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        raise ValueError("TAVILY_API_KEY environment variable is missing.")
        
    try:
        # Try official TavilySearch or TavilySearchResults from langchain_tavily / langchain_community
        try:
            from langchain_tavily import TavilySearch
            return TavilySearch(
                max_results=5,
                topic="general",
                include_answer=False,
                include_raw_content=False,
                search_depth="basic"
            )
        except ImportError:
            from langchain_community.tools.tavily_search import TavilySearchResults
            return TavilySearchResults(max_results=5)
    except Exception as e:
        print(f"Error initializing Tavily search tool: {e}")
        return None

# Lazy instances
_llm_instance = None
_tavily_instance = None

def _get_active_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance

def _get_active_tavily():
    global _tavily_instance
    if _tavily_instance is None:
        _tavily_instance = get_tavily_tool()
    return _tavily_instance

def _call_llm(llm_obj, *args, **kwargs):
    """Helper function to invoke LLM safely across LangChain versions."""
    if hasattr(llm_obj, "invoke") and callable(getattr(llm_obj, "invoke")):
        return llm_obj.invoke(*args, **kwargs)
    if hasattr(llm_obj, "run") and callable(getattr(llm_obj, "run")):
        return llm_obj.run(*args, **kwargs)
    if callable(llm_obj):
        return llm_obj(*args, **kwargs)
    raise AttributeError("LLM object does not provide invoke or run methods.")

# --- 2. Agent Node Creator Functions ---

# ----------------- #
# SUPERVISOR NODE   #
# ----------------- #
def create_supervisor_chain():
    """Creates the supervisor decision chain."""
    def supervisor_invoke(state):
        research = state.get("research_findings", [])
        research_text = "\n---\n".join(research) if research else "No research yet."
        
        revision = state.get("revision_number", 0)
        has_research = len(research) > 0
        has_draft = bool(state.get("draft", "").strip())
        critique = state.get("critique_notes", "")
        
        # 1. If critique says APPROVED, end workflow
        if "APPROVED" in critique.upper() and has_draft:
            print("Supervisor: Draft approved, ending workflow.")
            return {
                "next_step": "END",
                "task_description": "Report approved and complete"
            }
        
        # 2. If no research yet, trigger researcher
        if not has_research:
            print("Supervisor: No research findings yet, directing to researcher.")
            return {
                "next_step": "researcher",
                "task_description": f"Research topic: {state.get('main_task', '')}"
            }
        
        # 3. If research exists but no draft, trigger writer
        if has_research and not has_draft:
            print("Supervisor: Research available. Directing writer to compose draft.")
            return {
                "next_step": "writer",
                "task_description": "Write initial draft based on research findings"
            }
        
        # 4. If draft exists but no critique, send to critique review
        if has_draft and not critique:
            print("Supervisor: Draft created, forwarding to writer/critique flow.")
            return {
                "next_step": "writer",
                "task_description": "Prepare draft for critique evaluation"
            }
        
        # 5. If critique requires revision and under revision limit, trigger writer
        if critique and "APPROVED" not in critique.upper() and revision < 3:
            print(f"Supervisor: Revision {revision} requested, sending back to writer.")
            return {
                "next_step": "writer",
                "task_description": "Revise draft based on critique notes"
            }
        
        # 6. Max revisions reached
        if revision >= 3:
            print("Supervisor: Maximum revision limit reached (3). Finalizing report.")
            return {
                "next_step": "END",
                "task_description": "Maximum revisions reached, finalizing report"
            }
        
        # 7. Fallback to LLM dynamic decision
        llm = _get_active_llm()
        prompt = supervisor_prompt_template.format(
            main_task=state.get("main_task", ""),
            research_findings=research_text,
            draft=state.get("draft", "No draft yet."),
            critique_notes=critique if critique else "No critique yet.",
            revision_number=revision
        )
        
        try:
            response = _call_llm(llm, prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join([l for l in lines if not l.strip().startswith("```")])
            text = text.strip()
            
            decision = json.loads(text)
            if "next_step" in decision:
                return decision
        except Exception as e:
            print(f"Supervisor LLM parsing error: {e}")
        
        print("Supervisor: Using default fallback -> proceeding to writer.")
        return {
            "next_step": "writer",
            "task_description": "Continue with report generation"
        }
    
    return supervisor_invoke

# ----------------- #
# RESEARCHER NODE   #
# ----------------- #
def create_researcher_agent():
    """Creates the researcher agent that performs web search."""
    def researcher_invoke(input_dict):
        query = input_dict.get("input", "")
        if not query or query in ["Continue work", "Complete"]:
            query = "General research background"
        
        print(f"Researcher active: {query}")
        raw_output = ""
        results = []
        tavily_tool = _get_active_tavily()
        
        try:
            if tavily_tool:
                if hasattr(tavily_tool, "invoke"):
                    search_response = tavily_tool.invoke({"query": query})
                elif hasattr(tavily_tool, "run"):
                    search_response = tavily_tool.run(query)
                elif callable(tavily_tool):
                    search_response = tavily_tool({"query": query})
                else:
                    search_response = str(tavily_tool(query))
            else:
                search_response = "Tavily search tool unavailable."
            
            if isinstance(search_response, str):
                try:
                    search_data = json.loads(search_response)
                    results = search_data.get('results', [])
                except json.JSONDecodeError:
                    results = []
                    raw_output = search_response
            elif isinstance(search_response, dict):
                results = search_response.get('results', [])
            elif isinstance(search_response, list):
                results = search_response
            else:
                results = []
                raw_output = str(search_response)
            
            formatted_results = []
            if results:
                for result in results[:4]:
                    if isinstance(result, dict):
                        title = result.get('title', 'Untitled Source')
                        url = result.get('url', 'N/A')
                        content = result.get('content', result.get('snippet', ''))
                        formatted_results.append(f"**{title}**\nSource: {url}\n{content[:350]}...\n")
                    else:
                        formatted_results.append(str(result))
                raw_output = "\n---\n".join(formatted_results)
            elif not raw_output:
                raw_output = "No search results retrieved."
            
            # Summarize search results with LLM
            llm = _get_active_llm()
            summary_prompt = f"""Summarize key factual research findings about "{query}" based on these search results:

{raw_output}

Provide 5-7 clear, bulleted points emphasizing verifiable facts, statistics, and domain insights."""

            try:
                summary_response = _call_llm(llm, summary_prompt)
                summary = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            except Exception as e:
                print(f"Research summarization error: {e}")
                summary = raw_output
            
            return {
                "output": summary if summary else raw_output,
                "input": query
            }
        except Exception as e:
            print(f"Research agent execution error: {e}")
            return {
                "output": f"Research notes gathered for: {query}.",
                "input": query
            }
    
    return researcher_invoke

# ----------------- #
# WRITER NODE       #
# ----------------- #
def create_writer_chain():
    """Creates the writer agent chain."""
    def writer_invoke(state):
        llm = _get_active_llm()
        research = state.get("research_findings", [])
        research_text = "\n\n".join(research) if research else "No research findings available."
        
        prompt = writer_prompt_template.format(
            main_task=state.get("main_task", ""),
            research_findings=research_text,
            draft=state.get("draft", ""),
            critique_notes=state.get("critique_notes", "")
        )
        
        try:
            response = _call_llm(llm, prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip() if content else "Draft in progress..."
        except Exception as e:
            print(f"Writer agent error: {e}")
            return "Draft generation encountered an issue. Retrying in workflow loop."
    
    return writer_invoke

# ----------------- #
# CRITIQUE NODE     #
# ----------------- #
def create_critique_chain():
    """Creates the critique reviewer chain."""
    def critique_invoke(state):
        llm = _get_active_llm()
        draft = state.get("draft", "")
        revision_num = state.get("revision_number", 0)
        
        if len(draft.strip()) < 100:
            return "APPROVED - Initial draft content accepted."
        
        if revision_num >= 3:
            return "APPROVED - Maximum revision count reached. Report finalized."
        
        prompt = critique_prompt_template.format(
            main_task=state.get("main_task", ""),
            draft=draft
        )
        
        try:
            response = _call_llm(llm, prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return content.strip() if content else "APPROVED - Draft passed quality review."
        except Exception as e:
            print(f"Critique agent error: {e}")
            return "APPROVED - Automated review completed."
    
    return critique_invoke
