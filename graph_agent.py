from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from typing import TypedDict

from minio_read import get_deletable_tag, count_objects, delete_bucket
from policy import make_proposal, decide


class State(TypedDict):
    bucket: str
    deletable: str
    object_count: int
    decision: str
    result: str


def evaluate_node(state):
    deletable = get_deletable_tag(state["bucket"])
    count = count_objects(state["bucket"])
    proposal = make_proposal("delete_bucket", state["bucket"], deletable, count)
    decision = decide(proposal)
    return {"deletable": deletable, "object_count": count, "decision": decision}


def gate_node(state):
    # If policy blocked it, no human needed — stop here.
    if state["decision"] == "block":
        return {"result": "BLOCKED by policy — not deletable"}

    # Policy approved — pause and ask the human.
    answer = interrupt({
        "bucket": state["bucket"],
        "deletable": state["deletable"],
        "objects": state["object_count"],
        "ask": "Approve deletion of this bucket?",
    })

    if answer == "yes":
        msg = delete_bucket(state["bucket"])
        return {"result": f"EXECUTED: {msg}"}
    else:
        return {"result": "REJECTED by human"}


g = StateGraph(State)
g.add_node("evaluate", evaluate_node)
g.add_node("gate", gate_node)
g.add_edge(START, "evaluate")
g.add_edge("evaluate", "gate")
g.add_edge("gate", END)

app = g.compile(checkpointer=InMemorySaver())
