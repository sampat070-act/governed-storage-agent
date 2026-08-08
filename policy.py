def make_proposal(operation, bucket_name, deletable, object_count):
    return {
        "operation": operation,
        "bucket_name": bucket_name,
        "deletable": deletable,
        "object_count": object_count,
    }

def decide(proposal):
    if proposal["operation"] != "delete_bucket":
        return "block"
    if proposal["deletable"] != "true":
        return "block"
    return "approve"
