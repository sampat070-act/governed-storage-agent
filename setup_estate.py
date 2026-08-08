import boto3

s3 = boto3.client("s3", endpoint_url="http://localhost:9000",
                  aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin")

old = ["five9-call-recordings", "five9-voicemail", "five9-transcripts",
       "five9-databases", "five9-analytics"]
for b in old:
    try:
        s3.delete_bucket(Bucket=b)
        print(f"deleted {b}")
    except Exception as e:
        print(f"skip delete {b}: {e}")

estate = {
    "voice-call-recordings": {"environment": "prod", "data-classification": "restricted", "owner": "voice-platform", "retention": "permanent", "deletable": "false"},
    "voice-voicemail":       {"environment": "prod", "data-classification": "restricted", "owner": "voice-platform", "retention": "7-years",   "deletable": "false"},
    "voice-transcripts":     {"environment": "prod", "data-classification": "confidential","owner": "voice-platform", "retention": "3-years",   "deletable": "false"},
    "app-databases":         {"environment": "prod", "data-classification": "restricted", "owner": "app-team",       "retention": "permanent", "deletable": "false"},
    "app-analytics":         {"environment": "prod", "data-classification": "confidential","owner": "data-team",      "retention": "1-year",    "deletable": "false"},
    "finance-archive":       {"environment": "prod", "data-classification": "restricted", "owner": "finance",        "retention": "permanent", "deletable": "false"},
    "engineering-backups":   {"environment": "prod", "data-classification": "confidential","owner": "infra",          "retention": "90-days",   "deletable": "false"},
    "ai-storage-benchmark":  {"environment": "dev",  "data-classification": "internal",   "owner": "infra",          "retention": "30-days",   "deletable": "true"},
    "testsam":               {"environment": "test", "data-classification": "internal",   "owner": "sampat",         "retention": "7-days",    "deletable": "false"},
    "demo-empty":            {"environment": "test", "data-classification": "internal",   "owner": "sampat",         "retention": "1-day",     "deletable": "true"},
    "demo-full":             {"environment": "test", "data-classification": "internal",   "owner": "sampat",         "retention": "1-day",     "deletable": "true"},
}

for bucket, kv in estate.items():
    try:
        s3.create_bucket(Bucket=bucket)
        print(f"created {bucket}")
    except Exception:
        pass
    tagset = [{"Key": k, "Value": v} for k, v in kv.items()]
    s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tagset})
    print(f"tagged {bucket}: env={kv['environment']} deletable={kv['deletable']}")
