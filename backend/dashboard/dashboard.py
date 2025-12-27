import streamlit as st
import json
from confluent_kafka import Consumer
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="DevStream AI Dashboard",
    page_icon="🚀",
    layout="wide"
)

# Custom CSS for a modern "Card" look
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
    }
    div[data-testid="stExpander"] {
        border: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        background: white;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# Kafka Configuration
conf = {
    "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
    "group.id": "dashboard-group",
    "auto.offset.reset": "earliest",
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": os.getenv("KAFKA_API_KEY"),
    "sasl.password": os.getenv("KAFKA_API_SECRET"),
}

consumer = Consumer(conf)
consumer.subscribe(["ci_failures", "ci_ai_fixes"])

# Header Section
st.title("🚀 DevStream AI")
st.markdown("#### Real-Time CI Autoremediation Dashboard")

# Metrics Row
m1, m2, m3 = st.columns(3)
m1.metric("System Status", "Active", delta="Healthy")
m2.metric("AI Fixes Generated", "12", delta="+2")
m3.metric("PRs Merged", "8", delta="100%")

st.divider()

# Layout Columns
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 Incoming CI Failures")
    failures_box = st.container()

with col2:
    st.subheader("🤖 AI Analysis + Fixes")
    ai_box = st.container()

def render_diff(patch: str):
    """Render unified diff with color highlighting."""
    if not patch:
        return st.write("No patch produced.")
    st.code(patch, language="diff")

# Main Event Loop
while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        st.error(f"Consumer error: {msg.error()}")
        continue

    data = json.loads(msg.value().decode("utf-8"))

    # --- Incoming CI Failure ---
    if msg.topic() == "ci_failures":
        with failures_box:
            with st.chat_message("user", avatar="❌"):
                st.markdown("### CI Failure Received")
                with st.expander("📄 View Error Log", expanded=True):
                    st.code(data.get("log", ""), language="bash")
                with st.expander("🔍 View Source Code"):
                    st.code(data.get("code", ""), language="python")

    # --- AI Result (Fix + PR URL) ---
    elif msg.topic() == "ci_ai_fixes":
        with ai_box:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("### AI Remediation Plan")
                
                st.info(f"**Root Cause:** {data.get('root_cause', 'Analyzing...')}")
                
                st.markdown("**Explanation:**")
                st.write(data.get("explanation", "No explanation provided."))

                with st.expander("🛠️ View Proposed Patch", expanded=True):
                    render_diff(data.get("patch", ""))

                if "pr_url" in data:
                    st.success(f"✅ **Pull Request Created:** [Open GitHub PR]({data['pr_url']})")

                if "pr_error" in data:
                    st.error(f"⚠️ **PR Creation Failed:** {data['pr_error']}")