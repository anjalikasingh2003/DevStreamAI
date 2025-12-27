from confluent_kafka import Producer
import json
import os
from dotenv import load_dotenv
load_dotenv()

conf = {
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": os.getenv("KAFKA_API_KEY"),
    "sasl.password": os.getenv("KAFKA_API_SECRET"),
}

producer = Producer(conf)


def send_ci_failure(log_text, code_text):
    event = {
        "log": log_text,
        "code": code_text
    }
    producer.produce(
        topic="ci_failures",
        value=json.dumps(event).encode("utf-8")
    )
    producer.flush()
    print("Sent failure event → ci_failures")


if __name__ == "__main__":
    # --- Example simulated CI failure ---
    log = """
    E999 IndentationError: unexpected indent

    """

    code = """
def greet():
        print("Hello")
"""

    send_ci_failure(log, code)
