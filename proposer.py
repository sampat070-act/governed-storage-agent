import ollama


def propose(bucket, deletable, object_count, decision):
    facts = (
        f"Bucket name: {bucket}\n"
        f"Deletable tag: {deletable}\n"
        f"Object count: {object_count}\n"
        f"Policy decision: {decision}"
    )
    prompt = (
        "You are a storage operations assistant. Based ONLY on these facts, "
        "write a 2-sentence recommendation for a human reviewer about whether "
        "to delete this bucket. Do not invent facts.\n\n" + facts
    )
    resp = ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp["message"]["content"]
