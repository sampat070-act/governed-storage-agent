# graph_agent.py
# The orchestration layer. This is the LangGraph "app" that ties everything
# together: it reads facts, runs policy, pauses for a human, and acts.
# Flow:  START -> evaluate -> gate -> END

from langgraph.graph import StateGraph, START, END      # graph building blocks
from langgraph.types import interrupt                    # the pause-for-human mechanism
from typing import TypedDict                             # lets us define the shape of "state"

# Our own modules (the pieces this graph coordinates):
from minio_read import get_deletable_tag, count_objects, delete_bucket  # the hands (reads/acts on MinIO)
from policy import make_proposal, decide                                # the brain (deterministic decision)
from proposer import propose                                            # the narrator (LLM writes a note)
from audit import log_event                                             # the trail (logs every outcome)


# State = the bundle of information that travels through the graph.
# Each node reads from it and writes back into it.
class State(TypedDict):
    bucket: str          # which bucket we are evaluating (the input you provide)
    deletable: str       # its "deletable" tag, read from MinIO ("true"/"false")
    object_count: int    # how many objects are inside it
    decision: str        # what the policy decided ("block" or "approve")
    recommendation: str  # the LLM's plain-English note (shown to the human)
    result: str          # the final outcome text (BLOCKED / EXECUTED / REJECTED)


# NODE 1 - evaluate: read reality, then let policy decide. No human, no LLM here.
def evaluate_node(state):
    # Read the two real facts from MinIO:
    deletable = get_deletable_tag(state["bucket"])   # the tag ("true"/"false", "false" if untagged)
    count = count_objects(state["bucket"])           # object count

    # Bundle the facts into a proposal, then run the deterministic policy on it:
    proposal = make_proposal("delete_bucket", state["bucket"], deletable, count)
    decision = decide(proposal)                      # "block" or "approve"

    # Write the results back into state so the next node (gate) can use them:
    return {"deletable": deletable, "object_count": count, "decision": decision}


# NODE 2 - gate: act on the decision. Blocks, or pauses for a human, then deletes.
def gate_node(state):
    # Short names for readability (b=bucket, d=deletable, c=count, dec=decision):
    b, d, c, dec = state["bucket"], state["deletable"], state["object_count"], state["decision"]

    # --- BLOCK path: policy said no. Log it and stop. No human is even asked. ---
    if dec == "block":
        log_event(b, d, c, dec, "BLOCKED")
        return {"result": "BLOCKED by policy \u2014 not deletable"}

    # --- APPROVE path (only reached if NOT blocked) ---

    # Ask the LLM to write a recommendation from the REAL facts (advisory only):
    rec = propose(b, d, c, dec)

    # PAUSE HERE. interrupt() freezes the graph and shows the human the real facts
    # plus the LLM's note. The graph waits until a human resumes it with an answer.
    # Nothing has been deleted yet at this point.
    answer = interrupt({
        "bucket": b,
        "deletable": d,
        "objects": c,
        "llm_recommendation": rec,
        "ask": "Approve deletion of this bucket?",
    })

    # --- The human has now answered. ---
    if answer == "yes":
        msg = delete_bucket(b)                    # actually empties + deletes the bucket
        log_event(b, d, c, dec, "EXECUTED")       # record that it was executed
        return {"result": f"EXECUTED: {msg}", "recommendation": rec}
    else:
        log_event(b, d, c, dec, "REJECTED")       # human said no - record it
        return {"result": "REJECTED by human", "recommendation": rec}


# --- Wire the graph together ---
g = StateGraph(State)              # a graph that carries our State
g.add_node("evaluate", evaluate_node)
g.add_node("gate", gate_node)
g.add_edge(START, "evaluate")      # start -> evaluate
g.add_edge("evaluate", "gate")     # evaluate -> gate
g.add_edge("gate", END)            # gate -> end

# Compile into a runnable app. No checkpointer here on purpose:
# LangGraph Studio provides its own persistence when it runs this graph.
app = g.compile()
