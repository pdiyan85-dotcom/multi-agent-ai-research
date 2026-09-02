# main.py
"""CLI Entry point for Multi-Agent AI Research Assistant."""

import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_cli_research(topic: str, max_iterations: int = 15):
    """Executes the research graph via command-line interface."""
    from graph import app
    
    print(f"\n==========================================")
    print(f"  Multi-Agent AI Research Assistant (CLI)")
    print(f"  Topic: {topic}")
    print(f"==========================================\n")
    
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
    final_state = None
    
    try:
        for step in app.stream(initial_state, config=config):
            node_name = list(step.keys())[0]
            node_output = step[node_name]
            final_state = node_output
            print(f"[SUCCESS] Step completed by agent: {node_name.upper()}")
            
        print("\n==========================================")
        print("          FINAL RESEARCH REPORT           ")
        print("==========================================\n")
        
        draft = final_state.get("draft", "") if final_state else ""
        if draft:
            print(draft)
        else:
            print("No report draft was produced.")
            
    except Exception as e:
        print(f"\n[ERROR] CLI execution failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent AI Research Assistant CLI")
    parser.add_argument("--topic", type=str, help="Research topic or prompt")
    parser.add_argument("--iterations", type=int, default=15, help="Maximum recursion iterations")
    
    args = parser.parse_args()
    
    if args.topic:
        run_cli_research(args.topic, args.iterations)
    else:
        print("Multi-Agent AI Research Assistant initialized.")
        print("Run with Streamlit UI: streamlit run app.py")
        print("Run via CLI: python main.py --topic 'Your Topic Here'")

if __name__ == "__main__":
    main()
