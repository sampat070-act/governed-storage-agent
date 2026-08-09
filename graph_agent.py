from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from typing import TypedDict

from minio_read import get_deletable_tag, count_objects, delete_bucket
from policy import make_proposal, decide
from proposer import propose
from audit import log_event


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
    b, d, c, dec = state["bucket"], state["deletable"], state["object_count"], state["decision"]

    if dec == "block":
        log_event(b, d, c, dec, "BLOCKED")
        return {"result": "BLOCKED by policy \u2014 not deletable"}

    rec = propose(b, d, c, dec)

    answer = interrupt({
        "bucket": b,
        "deletable": d,
        "objects": c,
        "llm_recommendation": rec,
        "ask": "Approve deletion of this bucket?",
    })

    if answer == "yes":
        msg = delete_bucket(b)
        log_event(b, d, c, dec, "EXECUTED")
        return {"result": f"EXECUTED: {msg}", "recommendation": rec}
    else:
        log_event(b, d, c, dec, "REJECTED")
        return {"result": "REJECTED by human", "recommendation": rec}


g = StateGraph(State)
g.add_node("evaluate", evaluate_node)
g.add_node("gate", gate_node)
g.add_edge(START, "evaluate")
g.add_edge("evaluate", "gate")
g.add_edge("gate", END)

app = g.compile()
