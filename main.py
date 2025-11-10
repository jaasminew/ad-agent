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
    brand_identity: str
    draft: Optional[str]
    critique: Optional[str]
    final: Optional[str]
    pass_status: bool  # Track if critique passed
    iteration: int  # Track number of revisions
    max_iterations: int  # Prevent infinite loops

# ---------- Models ----------
logger.info("Initializing LLM models...")
writer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
critic_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
react_llm  = ChatOpenAI(model="gpt-4o-mini", temperature=0.6)
logger.info("✓ LLM models initialized")

# ---------- Prompts ----------
WRITER = PromptTemplate.from_template("""
You are a seasoned ad screenwriter.
Write a clear, slightly dramatic 60s product script in 8-10 beats. I want it to have an engaging storyline and message.
Return JSON:
{{
 "title": "...",
 "logline": "...",
 "beats": [
  {{"beat":1,"heading":"...","shot description":"...","action":"..."}},
  {{"beat":2,...}}, {{"beat":3,...}}, {{"beat":4,...}}, {{"beat":5,...}}
 ]}}
Product: {product}
Brand Identity: {brand_identity}
""")

CRITIC = PromptTemplate.from_template("""
Evaluate the draft. Score and diagnose; keep output compact.

Scoring (0–2 each; integers only):
- coherence in narrative structure, creative_storytelling, emotional_impact, visual_appeal, pacing, product_presence
Pass if total ≥ 11 AND no individual score is 0.

Diagnostics:
- issues: 3–6 items, each prefixed with tags like [coherence][beat2] or [visual_appeal]. Be specific and refer to beats when possible.
- must_fix: one imperative sentence (≤ 25 words) that, if applied, most increases the score next iteration.
- needs_research: 0–2 relevant screenwriting techniques to research in depth or "" if none. Make them specific (who/what/where/metric).

Constraints:
- No rewriting.
- No preambles or extra keys.
- If an area is solid, don’t invent problems.

Return JSON exactly in this shape:
{{
  "scores": {{
    "coherence": 0|1|2,
    "creative_storytelling": 0|1|2,
    "emotional_impact": 0|1|2,
    "visual_appeal": 0|1|2,
    "pacing": 0|1|2,
    "product_presence": 0|1|2
  }},
  "pass": true|false,
  "issues": ["..."],
  "must_fix": "...",
  "needs_research": "..."
}}

Script:
{draft}
""")

REACT_PROMPT = PromptTemplate.from_template("""
You are an autonomous ReAct agent improving an ad script. You will be receiving some critique from a creative director. You MUST analyze the critique and tailor some search queries to use web_search to help you gather techniques to improve the script.

Available tools: {tool_names}

{tools}

Critique from director: {critique}
Current draft (to be improved): {draft}
Product: {product}
Brand Identity: {brand_identity}
Tone: clear, slightly dramatic

WORKFLOW - Follow this exact sequence:
1) Use web_search: Analyze the critique and produce search queries to help you improve the script
2) Use remember: Store key findings from your searches
3) Use recall: Review your stored notes to prepare for revision
4) Final Answer: Take the CURRENT DRAFT and improve it by:
   - Incorporating specific techniques you found via web_search
   - Addressing all issues mentioned in the critique
   - Keeping the same structure
   - Maintaining the dramatic tone

CRITICAL INSTRUCTIONS:
- You have ONLY 3 tools: web_search, remember, recall
- There is NO "revise" or "update" tool - you revise the script yourself in the Final Answer
- After using web_search/remember/recall, directly output your improved script in Final Answer
- Your Final Answer should be the REVISED script, not a summary or explanation

FORMAT RULES:
- Keep each Thought concise (1-2 sentences max)
- After each Thought, either specify an Action OR give the Final Answer
- Do NOT output long explanations between Thought and Action
- The Final Answer must be valid JSON only, no extra text

Use this format EXACTLY:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I have gathered enough information, now I will revise the script
Final Answer: {{"title": "...", "logline": "...", "beats": [{{"beat":1,...}},{{"beat":2,...}},{{"beat":3,...}},{{"beat":4,...}},{{"beat":5,...}}...]}}


Begin!

Question: {input}
Thought:{agent_scratchpad}""")

# ---------- Nodes ----------
def write_node(state: ScriptState):
    logger.info("\n" + "="*60)
    logger.info("📝 Step 1: Writer Node - Generate Draft")
    logger.info("="*60)
    logger.info(f"Product: {state['product']}")
    logger.info(f"Brand Identity: {state['brand_identity']}")
    
    msg = WRITER.format(product=state["product"], brand_identity=state["brand_identity"])
    logger.info("Calling Writer LLM...")
    out = writer_llm.invoke(msg).content
    state["draft"] = out
    
    logger.info(f"✓ Draft generated (length: {len(out)} chars)")
    logger.info(f"Full draft:\n{out}")
    return state

def critique_node(state: ScriptState):
    logger.info("\n" + "="*60)
    logger.info(f"🔍 Step 2: Critic Node - Evaluate Script (Iteration {state.get('iteration', 0)})")
    logger.info("="*60)
    
    msg = CRITIC.format(draft=state["draft"])
    logger.info("Calling Critic LLM...")
    out = critic_llm.invoke(msg).content
    state["critique"] = out
    
    # Parse the critique to extract pass status
    import json
    try:
        critique_data = json.loads(out)
        state["pass_status"] = critique_data.get("pass", False)
        total_score = sum(critique_data.get("scores", {}).values())
        logger.info(f"✓ Critique completed - Pass: {state['pass_status']}, Total Score: {total_score}/12")
    except json.JSONDecodeError:
        logger.warning("⚠️  Failed to parse critique JSON, assuming not passed")
        state["pass_status"] = False
    
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
    iteration = state.get("iteration", 0) + 1
    state["iteration"] = iteration
    
    logger.info("\n" + "="*60)
    logger.info(f"🤖 Step 3: ReAct Agent - Iterative Improvement (Iteration {iteration})")
    logger.info("="*60)
    logger.info("Starting ReAct Agent (verbose=True)...")
    logger.info("Agent will show full reasoning (Thought/Action/Observation)")
    logger.info("-"*60)
    
    # Build input question, explicitly requiring web_search
    question = f"""You MUST improve this ad script by FIRST using web_search to gather facts.

Product: {state["product"]}
Brand Identity: {state["brand_identity"]}

Critique from director:
{state["critique"]}

Current Draft:
{state["draft"]}

Your task:
1. Use web_search to find real information about the product and brand identity
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
        "brand_identity": state["brand_identity"],
        "draft": state["draft"],
        "critique": state["critique"],
    })["output"]
    
    logger.info("\n" + "-"*60)
    logger.info("✓ ReAct Agent completed")
    logger.info(f"Final output length: {len(out)} chars")
    
    # Update the draft with the revised version for next iteration
    state["draft"] = out
    logger.info("✓ Draft updated with revised version for next critique")
    
    return state

# ---------- Decision Logic ----------
def should_continue(state: ScriptState) -> str:
    """Decide whether to continue revising or end the loop."""
    pass_status = state.get("pass_status", False)
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if pass_status:
        logger.info(f"✅ Script passed critique! Moving to finalize.")
        return "finalize"
    elif iteration >= max_iterations:
        logger.info(f"⚠️  Max iterations ({max_iterations}) reached. Moving to finalize.")
        return "finalize"
    else:
        logger.info(f"🔄 Script needs improvement. Starting revision cycle {iteration + 1}...")
        return "revise"

def finalize_node(state: ScriptState):
    """Finalize the script and store in final field."""
    logger.info("\n" + "="*60)
    logger.info("🎯 Finalizing Script")
    logger.info("="*60)
    
    state["final"] = state["draft"]
    
    if state.get("pass_status", False):
        logger.info("✅ Script passed all criteria!")
    else:
        logger.info("⚠️  Script did not pass, but max iterations reached. Using best version.")
    
    return state

# ---------- Graph ----------
logger.info("\nBuilding LangGraph workflow...")
graph = StateGraph(ScriptState)
graph.add_node("write", write_node)
graph.add_node("critique", critique_node)
graph.add_node("revise", react_revise_node)
graph.add_node("finalize", finalize_node)

# Build the flow with conditional loop
graph.add_edge(START, "write")
graph.add_edge("write", "critique")
graph.add_conditional_edges("critique", should_continue, {"revise": "revise", "finalize": "finalize"})
graph.add_edge("revise", "critique")  # Loop back to critique after revision
graph.add_edge("finalize", END)

app = graph.compile()
logger.info("✓ Workflow built: write -> critique -> [revise -> critique loop] -> finalize")

if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("Starting workflow execution")
    logger.info("="*60)
    
    init = {
        "product": "Polaroid Camera Now+ model", 
        "brand_identity": "Creative, expressive, rebellious",
        "iteration": 0,
        "max_iterations": 3,
        "pass_status": False
    }
    logger.info(f"Input parameters: {init}")
    logger.info(f"Max iterations allowed: {init['max_iterations']}")
    
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
    logger.info(f"  - Total iterations: {out.get('iteration', 0)}")
    logger.info(f"  - Final pass status: {out.get('pass_status', False)}")
    logger.info(f"  - Draft length: {len(out.get('draft', ''))} chars")
    logger.info(f"  - Critique length: {len(out.get('critique', ''))} chars")
    logger.info(f"  - Final version length: {len(out.get('final', ''))} chars")

