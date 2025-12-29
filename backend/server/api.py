from fastapi import FastAPI, Request, Header, HTTPException
from confluent_kafka import Producer
from datetime import datetime, timezone
import json, uuid, os, hmac, hashlib, re
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# ----------------------------
# KAFKA PRODUCER
# ----------------------------
producer = Producer({
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": os.getenv("KAFKA_API_KEY"),
    "sasl.password": os.getenv("KAFKA_API_SECRET"),
})

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


# Helper to clean text
def sanitize(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("\r", "")
            .replace("\t", "    ")
            .replace("\0", "")
            .strip()
    )


# ============================================================
# 1. CI FAILURE ENDPOINT
# ============================================================
@app.post("/api/send_ci_failure")
async def send_ci_failure(request: Request):
    try:
        body = await request.json()
    except:
        raw = await request.body()
        return {
            "status": "error",
            "message": "Invalid JSON",
            "raw_body": raw.decode()
        }

    required = ["repo_owner", "repo_name", "branch", "commit", "log", "code", "file_path"]
    missing = [k for k in required if k not in body]
    if missing:
        return {"status": "error", "message": f"Missing: {missing}"}

    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_owner": sanitize(body["repo_owner"]),
        "repo_name": sanitize(body["repo_name"]),
        "branch": sanitize(body["branch"]),
        "commit": sanitize(body["commit"]),
        "log": sanitize(body["log"])[:20000],
        "code": sanitize(body["code"])[:30000],
        "file_path": sanitize(body["file_path"]),
    }

    producer.produce("ci_failures", json.dumps(event).encode())
    producer.flush()

    return {"status": "success", "event_id": event["id"]}


# ============================================================
# 2. verify GitHub webhook
# ============================================================
def verify_signature(secret: str, body: bytes, signature_header: str):
    if not signature_header:
        raise HTTPException(status_code=400, detail="Missing X-Hub-Signature-256")

    sha, signature = signature_header.split("=")
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)

    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(status_code=400, detail="Invalid signature")


# ============================================================
# 3. Helper: Extract failure_id from branch name
# ============================================================
def extract_failure_id(branch: str):
    """
    Expected branch format:
    ai-fix-<failure_id>-<timestamp>
    """
    match = re.match(r"ai-fix-([a-f0-9-]+)-\d+", branch)
    if match:
        return match.group(1)
    return None


# ============================================================
# 4. GitHub Webhook Listener → produces ci_pr_updates
# ============================================================
@app.post("/api/github_webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    raw = await request.body()

    # Verify GitHub signature
    verify_signature(WEBHOOK_SECRET, raw, x_hub_signature_256)

    payload = json.loads(raw.decode())
    event_type = x_github_event

    # ==============================================
    # PULL REQUEST EVENTS
    # ==============================================
    if event_type == "pull_request":
        pr = payload["pull_request"]
        action = payload["action"]
        branch = pr["head"]["ref"]

        failure_id = extract_failure_id(branch)

        kafka_event = {
            "event": "pull_request",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "merged": pr.get("merged", False),
            "pr_number": pr["number"],
            "pr_url": pr["html_url"],
            "branch": branch,
            "failure_id": failure_id,
        }

        producer.produce("ci_pr_updates", json.dumps(kafka_event).encode())
        producer.flush()

        return {"status": "ok", "received": kafka_event}

    # ==============================================
    # IGNORE OTHER EVENTS
    # ==============================================
    return {"status": "ignored", "event": event_type}
