# ad_script_generator.py
import os
import logging
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from tools import web_search, remember, recall

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("="*60)
logger.info("Starting LangGraph ReAct Agent")
logger.info("="*60)

# ---------- State ----------
class ScriptState(TypedDict):
    product: str
    theme: str
    draft: Optional[str]
    critique: Optional[str]
    final: Optional[str]

# ---------- Models ----------
logger.info("Initializing LLM models...")
writer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
critic_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
react_llm  = ChatOpenAI(model="gpt-4o-mini", temperature=0.6)
logger.info("✓ LLM models initialized")

# ---------- Prompts ----------
WRITER = PromptTemplate.from_template("""
You are a seasoned ad screenwriter.
Write a clear, slightly dramatic 60–90s product script in exactly 5 beats.
Return JSON:
{{
 "title": "...",
 "logline": "...",
 "beats": [
  {{"beat":1,"heading":"...","voiceover":"...","action":"..."}},
  {{"beat":2,...}}, {{"beat":3,...}}, {{"beat":4,...}}, {{"beat":5,...}}
 ]}}
Product: {product}
Theme: {theme}
""")

CRITIC = PromptTemplate.from_template("""
You are a strict creative director. Critique the script and IDENTIFY what external information would improve it.
Evaluate: coherence, visual specificity, pacing (60–90s), product presence, tone, factual accuracy.

IMPORTANT: Point out missing facts, features, or context that need research.
Example issues: "lacks specific product features", "needs real beach vacation examples", "missing competitive advantages"

Return JSON:
{{"issues": ["issue1","issue2","issue3"], 
  "must_fix": "one sentence of fixes",
  "needs_research": "what facts/info should be searched for (be specific)"}}

Script:
{draft}
""")

REACT_PROMPT = PromptTemplate.from_template("""
You are an autonomous ReAct agent improving an ad script. You MUST use web_search to gather facts before revising.

Available tools:
{tools}

Brief (from critic): {critique}
Current draft: {draft}
Product: {product}
Theme: {theme}
Tone: clear, slightly dramatic

MANDATORY Process:
1) FIRST: Identify what needs research from the critique (especially 'needs_research' field)
2) THEN: Use web_search to find real facts, features, examples about the product and theme
3) Use remember to store key findings
4) Use recall if needed to review your notes
5) FINALLY: Revise the script with researched information
6) Output the improved script

IMPORTANT: You MUST call web_search at least once to gather factual information before making the final answer.
If the critique mentions "needs_research", search for that specific information.

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final JSON with format: {{"title": "...", "logline": "...", "beats": [{{"beat":1,...}},{{"beat":2,...}},{{"beat":3,...}},{{"beat":4,...}},{{"beat":5,...}}]}}

Begin!

Question: {input}
Thought:{agent_scratchpad}""")

# ---------- Nodes ----------
def write_node(state: ScriptState):
    logger.info("\n" + "="*60)
    logger.info("📝 Step 1: Writer Node - Generate Draft")
    logger.info("="*60)
    logger.info(f"Product: {state['product']}")
    logger.info(f"Theme: {state['theme']}")
    
    msg = WRITER.format(product=state["product"], theme=state["theme"])
    logger.info("Calling Writer LLM...")
    out = writer_llm.invoke(msg).content
    state["draft"] = out
    
    logger.info(f"✓ Draft generated (length: {len(out)} chars)")
    logger.info(f"Draft preview:\n{out[:200]}...")
    return state

def critique_node(state: ScriptState):
    logger.info("\n" + "="*60)
    logger.info("🔍 Step 2: Critic Node - Evaluate Script")
    logger.info("="*60)
    
    msg = CRITIC.format(draft=state["draft"])
    logger.info("Calling Critic LLM...")
    out = critic_llm.invoke(msg).content
    state["critique"] = out
    
    logger.info(f"✓ Critique completed (length: {len(out)} chars)")
    logger.info(f"Critique:\n{out}")
    return state

# ReAct agent with tools
logger.info("\nInitializing ReAct Agent and tools...")
tools = [web_search, remember, recall]
logger.info(f"Available tools: {[t.name for t in tools]}")
react_agent = create_react_agent(react_llm, tools, prompt=REACT_PROMPT)
react_exec  = AgentExecutor(
    agent=react_agent, 
    tools=tools, 
    verbose=True, 
    max_iterations=10,
    handle_parsing_errors=True  # Handle parsing errors, let Agent retry
)
logger.info("✓ ReAct Agent initialized")

def react_revise_node(state: ScriptState):
    logger.info("\n" + "="*60)
    logger.info("🤖 Step 3: ReAct Agent - Iterative Improvement")
    logger.info("="*60)
    logger.info("Starting ReAct Agent (verbose=True)...")
    logger.info("Agent will show full reasoning (Thought/Action/Observation)")
    logger.info("-"*60)
    
    # Build input question, explicitly requiring web_search
    question = f"""You MUST improve this ad script by FIRST using web_search to gather facts.

Product: {state["product"]}
Theme: {state["theme"]}

Critique from director:
{state["critique"]}

Current Draft:
{state["draft"]}

Your task:
1. Use web_search to find real information about the product and theme
2. Use remember to store key facts
3. Then revise the script with researched information
4. Return the improved version in JSON format

Start by searching for information!"""
    
    logger.info(f"Input question:\n{question[:300]}...")
    logger.info("-"*60)
    logger.info("⚠️  Note: Agent should use web_search tool first")
    logger.info("Starting ReAct reasoning loop...\n")
    
    out = react_exec.invoke({
        "input": question,
        "product": state["product"],
        "theme": state["theme"],
        "draft": state["draft"],
        "critique": state["critique"],
    })["output"]
    
    logger.info("\n" + "-"*60)
    logger.info("✓ ReAct Agent completed")
    logger.info(f"Final output length: {len(out)} chars")
    
    # Expect the agent to end with JSON output
    state["final"] = out
    return state

# ---------- Graph ----------
logger.info("\nBuilding LangGraph workflow...")
graph = StateGraph(ScriptState)
graph.add_node("write", write_node)
graph.add_node("critique", critique_node)
graph.add_node("revise", react_revise_node)
graph.add_edge(START, "write")
graph.add_edge("write", "critique")
graph.add_edge("critique", "revise")
graph.add_edge("revise", END)
app = graph.compile()
logger.info("✓ Workflow built: write -> critique -> revise")

if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("Starting workflow execution")
    logger.info("="*60)
    
    init = {"product": "Polaroid-style Instant Camera", "theme": "Golden-hour beach vacation"}
    logger.info(f"Input parameters: {init}")
    
    out = app.invoke(init)
    
    logger.info("\n" + "="*60)
    logger.info("Workflow execution completed")
    logger.info("="*60)
    
    print("\n" + "="*60)
    print("🎬 Final Script Output")
    print("="*60)
    print(out["final"])
    print("="*60)
    
    logger.info(f"\nSummary:")
    logger.info(f"  - Draft length: {len(out.get('draft', ''))} chars")
    logger.info(f"  - Critique length: {len(out.get('critique', ''))} chars")
    logger.info(f"  - Final version length: {len(out.get('final', ''))} chars")

