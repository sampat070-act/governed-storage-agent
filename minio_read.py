import boto3

import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_ENDPOINT"],
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
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



def show_estate():
    """Read-only report: every bucket with its deletable tag and object count (live from MinIO)."""
    print(f'{"BUCKET":22} {"DELETABLE":10} OBJECTS')
    print("-" * 44)
    for b in sorted(list_buckets()):
        print(f'{b:22} {get_deletable_tag(b):10} {count_objects(b)}')


if __name__ == "__main__":
    for b in list_buckets():
        print(b)


def delete_bucket(bucket_name):
    # S3 requires an empty bucket before deletion: remove objects first.
    objects = s3.list_objects_v2(Bucket=bucket_name).get("Contents", [])
    for obj in objects:
        s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
    s3.delete_bucket(Bucket=bucket_name)
    return f"deleted {bucket_name} ({len(objects)} objects removed)"
