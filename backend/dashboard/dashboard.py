import streamlit as st
import json
import time
from confluent_kafka import Consumer
import os
from dotenv import load_dotenv
import pandas as pd

# Load .env
load_dotenv()

def render_diff(diff_text):
    html = """
    <style>
    .diff-box { 
        font-family: 'JetBrains Mono', monospace; 
        background: #f8f9fa;
        padding: 12px; 
        border-radius: 6px; 
        border-left: 3px solid #4a90e2;
        font-size: 14px;
        white-space: pre-wrap;
        line-height: 1.4;
    }
    .diff-add { background: #e7f7ed; color: #137333; padding: 2px 4px; display: block; }
    .diff-del { background: #fdecea; color: #a33; padding: 2px 4px; display: block; }
    .diff-context { background: #f1f3f4; color: #333; padding: 2px 4px; display: block; }
    .diff-header { background: #e8f0fe; color: #174ea6; padding: 4px 4px; font-weight: bold; display: block; }
    </style>
    <div class='diff-box'>
    """

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            html += f"<div class='diff-header'>{line}</div>"
        elif line.startswith("@@"):
            html += f"<div class='diff-header'>{line}</div>"
        elif line.startswith("+"):
            html += f"<div class='diff-add'>{line}</div>"
        elif line.startswith("-"):
            html += f"<div class='diff-del'>{line}</div>"
        else:
            html += f"<div class='diff-context'>{line}</div>"

    html += "</div>"
    return html

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
        "group.id": "dashboard-final-v10",
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

if "last_message_ts" not in st.session_state:
    st.session_state.last_message_ts = None

if "kafka_latency" not in st.session_state:
    st.session_state.kafka_latency = []


# -----------------------------------------------------
# SYSTEM STATUS (NEW)
# -----------------------------------------------------
def compute_system_status():
    # Measure Kafka latency
    start = time.time()
    try:
        consumer.list_topics(timeout=1.5)
        kafka_up = True
    except:
        return ("🔴 DOWN", "Kafka unreachable", 999)

    latency_ms = (time.time() - start) * 1000
    st.session_state.kafka_latency.append(latency_ms)
    st.session_state.kafka_latency = st.session_state.kafka_latency[-30:]

    # Activity check
    ts = st.session_state.last_message_ts

    if ts is None:
        return ("🟡 Idle", "Waiting for first event", latency_ms)

    gap = time.time() - ts

    if gap < 60:
        heartbeat = "🟢 Active"
    elif gap < 300:
        heartbeat = "🟡 Idle"
    else:
        heartbeat = "🔴 Stale"

    return (heartbeat, f"Last event {int(gap)}s ago", latency_ms)


# -----------------------------------------------------
# HEADER
# -----------------------------------------------------
status, status_desc, kafka_latency = compute_system_status()

total_failures = len(st.session_state.builds)
total_fixes = len([b for b in st.session_state.builds.values() if b.get("fix")])

# PR Merge rate calculation
all_pr_events = []
for b in st.session_state.builds.values():
    all_pr_events.extend(b.get("pr", []))

total_pr_events = len(all_pr_events)
merged_count = len([e for e in all_pr_events if e.get("merged") is True])

merge_rate = (merged_count / total_pr_events * 100) if total_pr_events else 0

# METRICS ROW
m1, m2, m3, m4 = st.columns(4)
m1.metric("System Status", status, delta=status_desc)
m2.metric("Kafka Latency", f"{kafka_latency:.1f} ms")
m3.metric("PR Merge Success", f"{merge_rate:.1f}%")
m4.metric("Total Builds", total_failures)

st.divider()

# -----------------------------------------------------
# PR MERGE SPARKLINE GRAPH (NEW)
# -----------------------------------------------------
st.markdown("""
### 📈 PR Merge Success Trend
<small style='color:#666;'>Tracks how often AI-generated PRs are merged over time.</small>
""", unsafe_allow_html=True)
if total_pr_events > 0:
    df = pd.DataFrame({
        "merged": [1 if e.get("merged") else 0 for e in all_pr_events]
    })
    st.line_chart(df["merged"])
else:
    st.info("PR merge graph will appear after PR events start.")

st.divider()

# -----------------------------------------------------
# CONSUME ONE MESSAGE FROM KAFKA
# -----------------------------------------------------
msg = consumer.poll(0.5)

if msg and not msg.error():
    data = json.loads(msg.value().decode("utf-8"))
    st.session_state.last_message_ts = time.time()

    topic = msg.topic()

    # Match build ID
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
            st.session_state.builds[build_id]["pr"].append(data)

# -----------------------------------------------------
# SHOW BUILDS
# -----------------------------------------------------
for build_id, info in sorted(st.session_state.builds.items(), key=lambda x: x[1]["ts"], reverse=True):

    st.markdown(f"## 🧪 Build `{build_id}`")

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


    # PR TIMELINE
    st.subheader("📌 Pull Request Timeline")

    if fix and fix.get("pr_url"):
        st.markdown(f"""
            <div class="timeline-box status-created">
                🚀 PR Created<br>
                <small>{fix['pr_url']}</small>
            </div>
        """, unsafe_allow_html=True)

    for ev in info["pr"]:
        action = ev.get("action")
        merged = ev.get("merged")

        if merged is True:
            st.markdown("""
                <div class="timeline-box status-merged">
                    ✅ PR Merged into master
                </div>
            """, unsafe_allow_html=True)

        elif action == "closed":
            st.markdown("""
                <div class="timeline-box status-closed">
                    ❌ PR Closed (Not merged)
                </div>
            """, unsafe_allow_html=True)

        elif action == "opened":
            st.markdown("""
                <div class="timeline-box status-created">
                    📄 PR Opened
                </div>
            """, unsafe_allow_html=True)


    # -----------------------------------------------------
    # PR DIFF VIEWER (NEW)
    # -----------------------------------------------------
    st.subheader("📄 PR Diff Viewer")

    # Find the latest PR event for this build
    pr_events = info.get("pr", [])
    if len(pr_events) > 0:
        latest = pr_events[-1]
        pr_number = latest.get("pr_number")

        if pr_number:
            import requests

            owner = os.getenv("GITHUB_OWNER")
            repo = os.getenv("GITHUB_REPO")
            token = os.getenv("GITHUB_TOKEN")

            diff_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3.diff"
            }

            response = requests.get(diff_url, headers=headers)

            if response.status_code == 200:
                diff_text = response.text
                with st.expander(f"View Full Diff for PR #{pr_number}", expanded=False):
                    st.markdown(render_diff(diff_text), unsafe_allow_html=True)

            else:
                st.warning("⚠ Could not fetch PR diff. Check your GitHub token.")

    st.divider()

# -----------------------------------------------------
# AUTO REFRESH
# -----------------------------------------------------
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000)
