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
    font-family: "JetBrains Mono", monospace;
    font-size: 0.9rem;
    line-height: 1.45;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

.timeline-box {
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-size: 0.95rem;
    font-weight: 500;
}

.status-created { background: #e8f5ff; border-left: 4px solid #1a73e8; }
.status-merged  { background: #e7f7ed; border-left: 4px solid #0f9d58; }
.status-closed  { background: #fdecea; border-left: 4px solid #ea4335; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------
# KAFKA CONSUMER
# -----------------------------------------------------
@st.cache_resource
def get_consumer():
    conf = {
        "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
        "group.id": "dashboard-final-v7",
        "auto.offset.reset": "latest",
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": os.getenv("KAFKA_API_KEY"),
        "sasl.password": os.getenv("KAFKA_API_SECRET"),
    }
    c = Consumer(conf)
    c.subscribe(["ci_failures", "ci_ai_fixes", "ci_pr_updates"])
    return c

consumer = get_consumer()

# -----------------------------------------------------
# SESSION STATE
# -----------------------------------------------------
if "builds" not in st.session_state:
    st.session_state.builds = {}


# -----------------------------------------------------
# HEADER
# -----------------------------------------------------
st.title("🚀 DevStream AI — Live CI Autoremediation + PR Timeline Dashboard")

total_failures = len(st.session_state.builds)
total_fixes = len([b for b in st.session_state.builds.values() if b.get("fix")])
total_prs = len([b for b in st.session_state.builds.values() if b.get("pr")])

m1, m2, m3, m4 = st.columns(4)
m1.metric("System Status", "Active", delta="Healthy")
m2.metric("Failures", total_failures)
m3.metric("AI Fixes", total_fixes)
m4.metric("PR Events", total_prs)

st.divider()

# -----------------------------------------------------
# CONSUME ONE MESSAGE FROM KAFKA PER REFRESH
# -----------------------------------------------------
msg = consumer.poll(0.5)

if msg and not msg.error():
    data = json.loads(msg.value().decode("utf-8"))
    topic = msg.topic()

    # Determine build ID
    if topic == "ci_failures":
        build_id = data.get("id")
    else:
        build_id = data.get("failure_id")

    if build_id:
        if build_id not in st.session_state.builds:
            st.session_state.builds[build_id] = {"failure": None, "fix": None, "pr": [], "ts": time.time()}

        if topic == "ci_failures":
            st.session_state.builds[build_id]["failure"] = data

        elif topic == "ci_ai_fixes":
            st.session_state.builds[build_id]["fix"] = data

        elif topic == "ci_pr_updates":
            # Store multiple PR events
            st.session_state.builds[build_id]["pr"].append(data)


# -----------------------------------------------------
# RENDER BUILDS
# -----------------------------------------------------
for build_id, info in sorted(st.session_state.builds.items(), key=lambda x: x[1]["ts"], reverse=True):

    st.markdown(f"## 🧪 Build `{build_id}`")

    # -----------------------------------------------------
    # ROW 1 → FAILURE + FIX
    # -----------------------------------------------------
    c1, c2 = st.columns(2)

    # FAILURE
    with c1:
        fail = info["failure"]
        st.subheader("❌ CI Failure")

        if fail:
            st.markdown(f'<div class="log-box">{fail.get("log","")}</div>', unsafe_allow_html=True)
            with st.expander("Source Code"):
                st.code(fail.get("code", ""), language="python")
        else:
            st.info("Waiting for failure...")

    # FIX
    with c2:
        fix = info["fix"]
        st.subheader("🤖 AI Fix")

        if fix:
            st.info(f"Root Cause: {fix.get('root_cause','')}")
            st.write(fix.get("explanation", ""))

            with st.expander("Patch", expanded=True):
                st.code(fix.get("patch", ""), language="diff")

            if fix.get("pr_url"):
                st.success(f"PR Created → {fix['pr_url']}")
            elif fix.get("pr_error"):
                st.error(f"PR Error: {fix['pr_error']}")
        else:
            st.warning("⏳ AI is analyzing...")

    # -----------------------------------------------------
    # ROW 2 → PR TIMELINE (FULL WIDTH)
    # -----------------------------------------------------
    st.subheader("📌 Pull Request Timeline")

    pr_events = info["pr"]

    if fix and fix.get("pr_url"):
        st.markdown(f"""
            <div class="timeline-box status-created">
                🚀 PR Created<br>
                <small>{fix['pr_url']}</small>
            </div>
        """, unsafe_allow_html=True)

    if len(pr_events) == 0:
        st.info("Waiting for PR events...")
    else:
        for ev in pr_events:
            status = ev.get("status")
            action=ev.get("action")
            merged=ev.get("merged")

            # Merged PR
            if merged is True:
                st.markdown("""
                    <div class="timeline-box status-merged">
                        ✅ PR Merged into master
                    </div>
                """, unsafe_allow_html=True)

                        
            # Closed but NOT merged
            elif action == "closed":
                st.markdown("""
                    <div class="timeline-box status-closed">
                        ❌ PR Closed (Not merged)
                    </div>
                """, unsafe_allow_html=True)

            # PR opened
            elif action == "opened":
                st.markdown("""
                    <div class="timeline-box status-created">
                        🚀 PR Opened
                    </div>
                """, unsafe_allow_html=True)

    st.divider()


# -----------------------------------------------------
# AUTO REFRESH
# -----------------------------------------------------
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000)
