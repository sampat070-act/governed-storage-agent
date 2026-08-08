from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from typing import TypedDict

from minio_read import get_deletable_tag, count_objects, delete_bucket
from policy import make_proposal, decide
from proposer import propose


class State(TypedDict):
    bucket: str
    deletable: str
    object_count: int
    decision: str
    recommendation: str
    result: str


def evaluate_node(state):
    deletable = get_deletable_tag(state["bucket"])
    count = count_objects(state["bucket"])
    proposal = make_proposal("delete_bucket", state["bucket"], deletable, count)
    decision = decide(proposal)
    return {"deletable": deletable, "object_count": count, "decision": decision}


def gate_node(state):
    if state["decision"] == "block":
        return {"result": "BLOCKED by policy \u2014 not deletable"}

    # LLM narrates a recommendation from the REAL facts
    rec = propose(state["bucket"], state["deletable"], state["object_count"], state["decision"])

    # Pause and show the human BOTH the real facts and the LLM recommendation
    answer = interrupt({
        "bucket": state["bucket"],
        "deletable": state["deletable"],
        "objects": state["object_count"],
        "llm_recommendation": rec,
        "ask": "Approve deletion of this bucket?",
    })

    if answer == "yes":
        msg = delete_bucket(state["bucket"])
        return {"result": f"EXECUTED: {msg}", "recommendation": rec}
    else:
        return {"result": "REJECTED by human", "recommendation": rec}


g = StateGraph(State)
g.add_node("evaluate", evaluate_node)
g.add_node("gate", gate_node)
g.add_edge(START, "evaluate")
g.add_edge("evaluate", "gate")
g.add_edge("gate", END)

app = g.compile(checkpointer=InMemorySaver())
