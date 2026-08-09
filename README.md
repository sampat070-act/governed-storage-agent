# Governed Storage Agent

An agentic workflow for storage bucket deletion, built on [LangGraph](https://langchain-ai.github.io/langgraph/). The agent reads storage metadata autonomously but **never deletes anything without passing a deterministic policy check and a human approval gate.**

Built against a local [MinIO](https://min.io/) S3-compatible object store, using the same `boto3` calls that work against AWS S3 or any S3-compatible backend.

## The idea

Destructive storage operations shouldn't be fully automated, but the safe, repetitive parts can be. This agent follows the pattern most production teams have converged on: **read autonomously, gate the writes.**

- **The LLM advises. It never decides.** The delete/don't-delete decision is made by deterministic policy code, not the model. The LLM only writes a human-readable recommendation shown next to the real facts — so even if it hallucinates, it cannot cause a wrong action.
- **Deny-by-default.** A bucket is protected unless it is *explicitly* tagged `deletable=true`. No tag, wrong tag, or any read failure means protected.
- **Human-in-the-loop on every delete.** Every approved deletion pauses at an approval gate showing the real blast radius (object count) before a human confirms.
- **Full audit trail.** Every decision — blocked, executed, or rejected — is logged with a timestamp.

## Architecture

| File | Role |
|------|------|
| `minio_read.py` | **The hands.** Reads live from MinIO — lists buckets, reads the `deletable` tag, counts objects. Returns `false` (protected) on any doubt (deny-by-default). |
| `policy.py` | **The brain.** Deterministic. Blocks anything that isn't a delete of an explicitly `deletable=true` bucket. No LLM involved. |
| `proposer.py` | **The narrator.** A local LLM (llama3.2 via Ollama) turns the real facts into a plain-English recommendation for the human. Advisory only. |
| `graph_agent.py` | **The orchestration.** A LangGraph graph: `evaluate` reads facts and runs policy, `gate` blocks or pauses at `interrupt()` for human approval, then executes the real delete. |
| `audit.py` | **The trail.** Appends one JSON record per decision to `audit.log`. |
| `setup_estate.py` | One-time seed: creates and tags a realistic bucket estate for testing. |
| `test_policy.py` | Tests for the policy engine. |

## Flow

```
                 +-------------+
   bucket name ->|  evaluate   |  reads deletable tag + object count from MinIO,
                 |   node      |  runs deterministic policy -> block or approve
                 +------+------+
                        v
                 +-------------+
                 |   gate      |  BLOCKED?  -> log, stop. No human asked.
                 |   node      |  APPROVED? -> LLM writes recommendation,
                 +------+------+             then interrupt() PAUSES for human
                        v
              human approves? --yes--> empty bucket, delete it, log EXECUTED
                        |
                        +----no------> log REJECTED, nothing deleted
```

## Guardrail philosophy

Three independent layers, each of which must pass:

1. **Policy (deterministic):** deny-by-default — protected unless explicitly `deletable=true`.
2. **LLM (advisory):** describes the situation to the human, but has no authority to act. Facts come from MinIO, not the model.
3. **Human (approval):** sees the real object count (blast radius) and gives the final yes/no.

A hallucinating model, a mislabeled bucket, or a wrong operation is caught by at least one layer before anything is deleted.

## Running it

Requires a local MinIO at `localhost:9000` and [Ollama](https://ollama.com/) with `llama3.2` pulled.

```bash
# 1. Set up environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Credentials (never committed) live in .env
cp .env.example .env   # then edit with your MinIO credentials

# 3. Seed a test bucket estate (one time)
python setup_estate.py

# 4a. Run the tests
python test_policy.py

# 4b. Or drive it visually in LangGraph Studio
langgraph dev
# then open the Studio URL in Chrome, submit a bucket name,
# approve or reject at the gate
```

## Production notes

This is a portfolio demo; the same design scales with a few changes:

- **Tags at creation, not hardcoded.** In production, buckets carry tags like `environment`, `data-classification`, and `retention` set at provisioning time (e.g. via Terraform). The agent reads those; it never maintains a hardcoded list.
- **Scales by metadata, not name lists.** Because decisions ride on tags, the policy works for any number of buckets without code changes. Listing thousands of buckets would use pagination.
- **Secrets via a manager, not `.env`.** Local dev uses a gitignored `.env`; production would fetch short-lived credentials from a secrets manager or IAM role, holding no long-lived secret.
- **Swappable LLM.** The narrator runs locally on Ollama (no key, no cost) and swaps to a hosted model with a one-line change.
- **Durable state.** The demo uses an in-memory checkpointer; production would back the graph with Postgres for durable, replayable state.

## Stack

Python · LangGraph · boto3 · MinIO · Ollama (llama3.2) · python-dotenv
