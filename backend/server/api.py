from fastapi import FastAPI, Request, Header, HTTPException
from confluent_kafka import Producer
from datetime import datetime, timezone
import json, uuid, os, hmac, hashlib, re
from dotenv import load_dotenv
from server.notifier import notify_slack, send_email
import requests

load_dotenv()
app = FastAPI()
from google.cloud import firestore

db = firestore.Client()
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
        if action == "opened":
            notify_slack(f"📄 PR #{pr['number']} opened: {pr['html_url']}")
            send_email("anjalikasingh1603@gmail.com", "PR Opened", f"A PR has been opened:\n{pr['html_url']}")

        elif action == "closed" and pr.get("merged"):
            notify_slack(f"🎉 PR #{pr['number']} merged successfully!")
            send_email("anjalikasingh1603@gmail.com", "PR Merged", f"PR merged:\n{pr['html_url']}")

        elif action == "closed":
            notify_slack(f"❌ PR #{pr['number']} was closed without merging")
            send_email("anjalikasingh1603@gmail.com", "PR Closed", f"PR closed:\n{pr['html_url']}")

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
            "repo_owner": payload["repository"]["owner"]["login"],
            "repo_name": payload["repository"]["name"],
        }

        producer.produce("ci_pr_updates", json.dumps(kafka_event).encode())
        producer.flush()

        return {"status": "ok", "received": kafka_event}

    # ==============================================
    # IGNORE OTHER EVENTS
    # ==============================================
    return {"status": "ignored", "event": event_type}


@app.post("/api/register_repo")
async def register_repo(request: Request):
    data = await request.json()

    repo_url = data.get("repo_url")
    if not repo_url:
        return {"status": "error", "message": "Missing repo_url"}

    # Extract owner/repo
    try:
        # Example: https://github.com/anjalika/Dummy
        owner, repo = repo_url.rstrip("/").split("/")[-2:]
        full_name = f"{owner}/{repo}"
    except:
        return {"status": "error", "message": "Invalid GitHub repo URL"}
    # Firestore document ID = owner_repo
    doc_id = f"{owner}_{repo}"
    
    repo_ref = db.collection("repos").document(doc_id)
    repo_ref.set({
        "owner": owner,
        "repo": repo,
        "full_name": full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }, merge=True)

    # Return YAML template auto-generated for user
    github_yaml = """
    name: DevStreamAI CI

on:
  push:
    branches: ["master", "main"]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Add project root to PYTHONPATH
        run: echo "PYTHONPATH=$(pwd)" >> $GITHUB_ENV

      - name: Run tests
        id: tests
        continue-on-error: true
        run: |
          echo "Running tests..."
          pytest --maxfail=1

      - name: Send CI failure to DevStream AI
        if: ${{ steps.tests.outcome == 'failure' }}
        run: |
          echo "❌ Tests failed — sending details to DevStream AI..."

          ERROR_LOG=$(pytest --maxfail=1 2>&1 || true)

          FILE_PATH=$(git diff --name-only HEAD~1 HEAD 2>/dev/null | grep ".py" | head -n 1 || true)
          if [ -z "$FILE_PATH" ]; then
              FILE_PATH=$(echo "$ERROR_LOG" | grep -oP '(?<=File ")[^"]+\.py' | head -n 1)
          fi
          if [ -z "$FILE_PATH" ]; then
              FILE_PATH=$(echo "$ERROR_LOG" | grep -oP "src/[A-Za-z0-9_\/]+\.py" | head -n 1)
          fi
          if [ -z "$FILE_PATH" ]; then
              FILE_PATH=$(find . -type f -name "*.py" | head -n 1)
          fi

          echo "📌 Detected failing file: $FILE_PATH"

          CODE_CONTENT=$(sed ':a;N;$!ba;s/\n/\\n/g' "$FILE_PATH" | sed 's/"/\\"/g')
          ESCAPED_LOG=$(printf "%s" "$ERROR_LOG" | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/\\"/g')

          curl -X POST "${{ secrets.DEVSTREAM_WEBHOOK }}" \
            -H "Content-Type: application/json" \
            -d "{
              \"repo_owner\": \"${{ github.repository_owner }}\",
              \"repo_name\": \"${{ github.event.repository.name }}\",
              \"branch\": \"${GITHUB_REF_NAME}\",
              \"commit\": \"${GITHUB_SHA}\",
              \"log\": \"$ESCAPED_LOG\",
              \"file_path\": \"$FILE_PATH\",
              \"code\": \"$CODE_CONTENT\"
            }"

      - name: Success message
        if: ${{ steps.tests.outcome == 'success' }}
        run: echo "✔ CI passed without errors."
    """

    return {
        "status": "success",
        "repo": full_name,
        "yaml_template": github_yaml
    }


