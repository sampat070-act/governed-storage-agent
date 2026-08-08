from minio_read import get_deletable_tag, count_objects
from policy import make_proposal, decide

def evaluate_delete(bucket_name):
    deletable = get_deletable_tag(bucket_name)
    count = count_objects(bucket_name)
    proposal = make_proposal("delete_bucket", bucket_name, deletable, count)
    decision = decide(proposal)
    return proposal, decision

if __name__ == "__main__":
    for bucket in ["demo-full", "demo-empty", "finance-archive", "testsam"]:
        proposal, decision = evaluate_delete(bucket)
        print(f"{bucket:20} deletable={proposal['deletable']:6} objects={proposal['object_count']} -> {decision}")
