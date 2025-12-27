from fastapi import FastAPI, Request
from confluent_kafka import Producer
from datetime import datetime, timezone
import json, uuid, os
from dotenv import load_dotenv
load_dotenv()
app = FastAPI()

producer = Producer({
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": os.getenv("KAFKA_API_KEY"),
    "sasl.password": os.getenv("KAFKA_API_SECRET"),
})


def sanitize(text: str) -> str:
    """Make sure text is safe to send over JSON → Kafka."""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("\r", "")
            .replace("\t", "    ")
            .replace("\0", "")
            .strip()
    )


@app.post("/api/send_ci_failure")
async def send_ci_failure(request: Request):
    # --- STEP 1: Try to parse JSON normally ---
    try:
        body = await request.json()
    except Exception as e:
        raw = await request.body()
        return {
            "status": "error",
            "message": f"Invalid JSON from GitHub: {e}",
            "raw_body": raw.decode("utf-8", errors="ignore")
        }

    # --- STEP 2: Validate keys ---
    required = ["repo_owner", "repo_name", "branch", "commit", "log", "code", "file_path"]
    missing = [k for k in required if k not in body]

    if missing:
        return {
            "status": "error",
            "message": f"Missing keys: {missing}",
            "received_keys": list(body.keys())
        }

    # --- STEP 3: Clean incoming data ---
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

    # --- STEP 4: Send to Kafka ---
    try:
        producer.produce("ci_failures", json.dumps(event).encode("utf-8"))
        producer.flush()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Kafka produce failed: {e}"
        }

    return {"status": "success", "event_id": event["id"]}
