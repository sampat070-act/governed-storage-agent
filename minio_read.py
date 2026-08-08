import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
)

def list_buckets():
    return [b["Name"] for b in s3.list_buckets()["Buckets"]]

def get_deletable_tag(bucket_name):
    try:
        resp = s3.get_bucket_tagging(Bucket=bucket_name)
        for tag in resp["TagSet"]:
            if tag["Key"] == "deletable":
                return tag["Value"]
        return "false"
    except Exception:
        return "false"

def count_objects(bucket_name):
    resp = s3.list_objects_v2(Bucket=bucket_name)
    return resp.get("KeyCount", 0)

if __name__ == "__main__":
    for b in list_buckets():
        print(b)


def delete_bucket(bucket_name):
    s3.delete_bucket(Bucket=bucket_name)
    return f"deleted {bucket_name}"
