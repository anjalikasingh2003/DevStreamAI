from confluent_kafka import Consumer, Producer
import json
import os
from ..ai.ai_engine import analyze_failure
from ..github.pr_creator import create_pr_from_patch
from dotenv import load_dotenv

load_dotenv()

conf = {
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
    "group.id": "devstream-ai-group-1",
    "auto.offset.reset": "earliest",
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": os.getenv("KAFKA_API_KEY"),
    "sasl.password": os.getenv("KAFKA_API_SECRET"),
}

consumer = Consumer(conf)

producer = Producer(conf)

consumer.subscribe(["ci_failures"])

def send_fix(result):
    producer.produce(
        topic="ci_ai_fixes",
        value=json.dumps(result).encode("utf-8")
    )
    producer.flush()
    print("AI Fix published → ci_ai_fixes")


def run_agent():
    print("Listening for CI failures...")

    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            print("Consumer error:", msg.error())
            continue

        data = json.loads(msg.value().decode("utf-8"))

        log = data["log"]
        code = data["code"]

        print("\n📥 Incoming Failure Event:")
        print(log)
        # --- STEP 1: Analyze failure using AI Engine ---
        # Call AI Engine
        ai_output = analyze_failure(log, code)

        print("\n🤖 AI Output:")
        print(ai_output)
         # --- STEP 2: Create PR from AI patch ---
        try:
            patch = ai_output.get("patch")
            explanation = ai_output.get("explanation", "")

            if not patch:
                print("⚠️ No patch produced by AI. Skipping PR.")
                continue

            print("\n🛠️ Creating PR...")
            file_path = data.get("file_path")
            pr_url = create_pr_from_patch(patch, explanation, file_path)
            ai_output["pr_url"] = pr_url

            print("🚀 PR Created Successfully:", pr_url)

        except Exception as e:
            print("❌ Error while creating PR:", e)
            ai_output["pr_error"] = str(e)

        # publish AI result
        send_fix(ai_output)


if __name__ == "__main__":
    run_agent()
