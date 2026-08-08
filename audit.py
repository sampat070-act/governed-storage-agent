import json
from datetime import datetime


def log_event(bucket, deletable, object_count, decision, outcome):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "bucket": bucket,
        "deletable": deletable,
        "object_count": object_count,
        "policy_decision": decision,
        "outcome": outcome,
    }
    with open("audit.log", "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
