import streamlit as st
import json
import time
from confluent_kafka import Consumer
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# -----------------------------------------------------
# PAGE CONFIG + CSS
# -----------------------------------------------------
st.set_page_config(page_title="DevStream AI Dashboard", page_icon="🚀", layout="wide")

st.markdown("""
<style>
.log-box {
    max-height: 350px;
    overflow-y: auto;

    background: #f4f6fb;
    border-left: 4px solid #4a90e2;
    padding: 14px;

    color: #2b2b2b;
    border-radius: 6px;

    font-family: "JetBrains Mono", "Source Code Pro", monospace;
    font-size: 0.90rem;
    line-height: 1.45;

    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------
# KAFKA CONSUMER (Cached)
# -----------------------------------------------------
@st.cache_resource
def get_consumer():
    conf = {
        "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
        "group.id": "dashboard-final-v4",
        "auto.offset.reset": "latest",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": os.getenv("KAFKA_API_KEY"),
        "sasl.password": os.getenv("KAFKA_API_SECRET"),
    }
    c = Consumer(conf)
    c.subscribe(["ci_failures", "ci_ai_fixes"])
    return c

consumer = get_consumer()

# -----------------------------------------------------
# SESSION STATE (INITIALIZE ONCE)
# -----------------------------------------------------
if "builds" not in st.session_state:
    st.session_state.builds = {}

# -----------------------------------------------------
# HEADER
# -----------------------------------------------------
st.title("🚀 DevStream AI — Live CI Autoremediation Dashboard")

total_failures = len(st.session_state.builds)
total_fixes = len([b for b in st.session_state.builds.values() if b["fix"]])

m1, m2, m3 = st.columns(3)
m1.metric("System Status", "Active", delta="Healthy")
m2.metric("Failures Detected", total_failures)
m3.metric("AI Fixes Generated", total_fixes)

st.divider()

# -----------------------------------------------------
# POLL KAFKA FOR NEW EVENT (ONCE PER REFRESH)
# -----------------------------------------------------
msg = consumer.poll(0.5)

if msg and not msg.error():
    data = json.loads(msg.value().decode("utf-8"))

    if msg.topic() == "ci_failures":
        build_id = data.get("id")
    else:
        build_id = data.get("failure_id")

    if build_id:
        if build_id not in st.session_state.builds:
            st.session_state.builds[build_id] = {"failure": None, "fix": None, "ts": time.time()}

        if msg.topic() == "ci_failures":
            st.session_state.builds[build_id]["failure"] = data
        else:
            st.session_state.builds[build_id]["fix"] = data

# -----------------------------------------------------
# DISPLAY PAIRED FAILURES + FIXES
# -----------------------------------------------------
for build_id, info in sorted(st.session_state.builds.items(), key=lambda x: x[1]["ts"], reverse=True):
    st.markdown(f"### 🧪 Build ID: `{build_id}`")
    col1, col2 = st.columns(2)

    # LEFT → CI FAILURE
    with col1:
        fail = info["failure"]
        if fail:
            st.subheader("❌ CI Failure")
            st.markdown(f'<div class="log-box">{fail.get("log","")}</div>', unsafe_allow_html=True)

            with st.expander("Source Code"):
                st.code(fail.get("code", ""), language="python")
        else:
            st.info("Waiting for failure...")

    # RIGHT → AI FIX
    with col2:
        fix = info["fix"]
        if fix:
            st.subheader("🤖 AI Remediation")
            st.info(f"Root Cause: {fix.get('root_cause','')}")
            st.write(fix.get("explanation", ""))

            with st.expander("Proposed Patch", expanded=True):
                st.code(fix.get("patch", ""), language="diff")

            if fix.get("pr_url"):
                st.success(f"PR Created → {fix['pr_url']}")
            if fix.get("pr_error"):
                st.error(f"PR Error: {fix['pr_error']}")
        else:
            st.warning("⏳ AI is analyzing this failure...")

    st.divider()
# -----------------------------------------------------
# AUTO-REFRESH EVERY 2 SECONDS
# -----------------------------------------------------
st_autorefresh = st.experimental_rerun if hasattr(st, "experimental_rerun") else None

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000, limit=None)
