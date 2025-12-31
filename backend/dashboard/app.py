import streamlit as st
import json
import time
from confluent_kafka import Consumer
import os
from dotenv import load_dotenv
import pandas as pd
import requests

# Load environment variables
load_dotenv()

# Constants
API_URL = "https://devstream-backend-176657413002.us-central1.run.app"
REG_FILE = "registered_repos.json"

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="DevStream AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'home'

if "builds" not in st.session_state:
    st.session_state.builds = {}

if "last_message_ts" not in st.session_state:
    st.session_state.last_message_ts = None

if "kafka_latency" not in st.session_state:
    st.session_state.kafka_latency = []

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def load_registered_repos():
    if os.path.exists(REG_FILE):
        with open(REG_FILE, 'r') as f:
            return json.load(f)
    return []

def save_registered_repo(repo_name):
    """Save repository to local JSON file"""
    repos = load_registered_repos()
    if repo_name not in repos:
        repos.append(repo_name)
        with open(REG_FILE, 'w') as f:
            json.dump(repos, f, indent=2)

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

# ---------------------------------------------------------
# GLOBAL CSS
# ---------------------------------------------------------
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .hero-section {
        text-align: center;
        padding: 3rem 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .hero-subtitle {
        font-size: 1.3rem;
        opacity: 0.95;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border-left: 4px solid #667eea;
        transition: transform 0.2s;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    .instruction-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #4a90e2;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #e7f7ed;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #0f9d58;
        margin: 1rem 0;
    }
    
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
    
    .stButton > button {
        width: 100%;
        padding: 1rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# PAGE: HOME / LANDING
# =============================================================================
def show_home_page():
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">🚀 DevStream AI</div>
        <div class="hero-subtitle">
            Intelligent CI/CD Automation powered by AI & Kafka
        </div>
        <p style="font-size: 1rem; opacity: 0.9;">
            Automatically detect failures, generate fixes, and track PRs in real-time
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🎯 Quick Start")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">🔗</div>
            <div style="font-size: 1.4rem; font-weight: 600; margin-bottom: 0.5rem;">Connect Repository</div>
            <div style="color: #666; line-height: 1.6;">
                Link your GitHub repository and set up automated CI monitoring with AI-powered fix generation.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔗 Connect New Repository", type="primary", use_container_width=True):
            st.session_state.page = 'connect'
            st.rerun()

    with col2:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 2.5rem; margin-bottom: 1rem;">📊</div>
            <div style="font-size: 1.4rem; font-weight: 600; margin-bottom: 0.5rem;">View Dashboard</div>
            <div style="color: #666; line-height: 1.6;">
                Monitor CI failures, AI-generated fixes, and PR status in real-time with live Kafka streams.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📊 Open Dashboard", type="secondary", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()

    st.markdown("---")
    st.markdown("## ✨ Key Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 🤖 AI-Powered Analysis
        - Automatic failure detection
        - Root cause analysis
        - Smart fix generation
        - Context-aware solutions
        """)

    with col2:
        st.markdown("""
        ### ⚡ Real-Time Processing
        - Kafka event streaming
        - Live dashboard updates
        - Instant notifications
        - Low-latency pipeline
        """)

    with col3:
        st.markdown("""
        ### 🔄 Complete Automation
        - Auto-generated PRs
        - CI/CD integration
        - PR lifecycle tracking
        - Merge success metrics
        """)

# =============================================================================
# PAGE: CONNECT REPOSITORY
# =============================================================================
def show_connect_page():
    st.title("🔗 Connect Your GitHub Repository")

    st.markdown("""
    Connect your repository to enable **DevStreamAI's** intelligent CI/CD automation:
    """)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("✅ **Real-time CI Monitoring**")
    with col2:
        st.markdown("🤖 **AI-Powered Fixes**")
    with col3:
        st.markdown("🚀 **Automated PRs**")

    st.markdown("---")
    st.markdown("## 📝 Step 1: Enter Repository URL")

    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/username/repository",
        help="Example: https://github.com/octocat/hello-world",
        label_visibility="collapsed"
    )

    st.markdown("""
    <div class="instruction-box">
        <strong>💡 Tip:</strong> Make sure you have admin access to this repository to add webhooks and secrets.
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("⬅️ Back to Home", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
    
    with col_btn2:
        submit = st.button("🚀 Connect Repository", type="primary", use_container_width=True)

    if submit:
        if not repo_url.strip():
            st.error("❗ Please provide a valid GitHub repository URL.")
        else:
            with st.spinner("🔄 Registering your repository..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/api/register_repo",
                        json={"repo_url": repo_url},
                        timeout=10
                    )
                except Exception as e:
                    st.error(f"❌ API connection failed: {e}")
                    st.stop()

            if resp.status_code != 200:
                st.error(f"❌ Backend Error:\n{resp.text}")
                st.stop()

            try:
                data = resp.json()
            except:
                st.error("❌ Invalid response from backend")
                st.stop()

            if data.get("status") != "success":
                st.error(f"❌ Error: {data.get('message', 'Unknown error')}")
                st.stop()

            repo_full_name = data.get('repo')
            if repo_full_name:
                save_registered_repo(repo_full_name)

            st.balloons()
            
            st.markdown(f"""
            <div class="success-box">
                <h3>✅ Repository Successfully Connected!</h3>
                <p><strong>Repository:</strong> {repo_full_name}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("## ⚙️ Step 2: Add CI Workflow")
            st.markdown("Copy the workflow file below and save it to: `.github/workflows/devstream.yml`")
            st.code(data.get("yaml_template", ""), language="yaml")

            st.markdown("## 🔐 Step 3: Configure GitHub Secret")
            st.markdown("""
            <div class="instruction-box">
                <p><strong>1.</strong> Go to: Settings → Secrets and variables → Actions</p>
                <p><strong>2.</strong> Click "New repository secret"</p>
                <p><strong>3.</strong> Name: <code>DEVSTREAM_WEBHOOK</code></p>
                <p><strong>4.</strong> Value: <code>https://devstream-backend-176657413002.us-central1.run.app/api/send_ci_failure</code></p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            if st.button("📊 Go to Dashboard →", type="primary", use_container_width=True):
                st.session_state.page = 'dashboard'
                st.rerun()

# =============================================================================
# PAGE: DASHBOARD
# =============================================================================
def show_dashboard_page():
    st.title("📊 DevStream AI Dashboard")
    st.markdown("Real-time monitoring of CI failures, AI fixes, and PR lifecycle")

    # Sidebar
    st.sidebar.title("📁 Repositories")
    repos = load_registered_repos()

    if len(repos) == 0:
        st.sidebar.warning("⚠️ No repositories connected")
        st.info("👋 No repositories connected yet.")
        
        if st.button("🔗 Connect Repository", type="primary"):
            st.session_state.page = 'connect'
            st.rerun()
        
        if st.button("⬅️ Back to Home"):
            st.session_state.page = 'home'
            st.rerun()
        st.stop()

    selected_repo = st.sidebar.selectbox("Select Repository", repos)
    st.sidebar.success(f"✅ Monitoring: **{selected_repo}**")

    if st.sidebar.button("➕ Connect Another"):
        st.session_state.page = 'connect'
        st.rerun()
    
    if st.sidebar.button("🏠 Home"):
        st.session_state.page = 'home'
        st.rerun()

    # Kafka Consumer
    @st.cache_resource
    def get_consumer():
        conf = {
            "bootstrap.servers": os.getenv("CONFLUENT_BOOTSTRAP"),
            "group.id": "dashboard-v12",
            "auto.offset.reset": "latest",
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "PLAIN",
            "sasl.username": os.getenv("KAFKA_API_KEY"),
            "sasl.password": os.getenv("KAFKA_API_SECRET"),
        }
        c = Consumer(conf)
        c.subscribe(["ci_failures", "ci_ai_fixes", "ci_pr_updates"])
        return c

    try:
        consumer = get_consumer()
    except Exception as e:
        st.error(f"❌ Kafka connection failed: {e}")
        return

    # System Status
    def compute_system_status():
        start = time.time()
        try:
            consumer.list_topics(timeout=1.5)
        except:
            return ("🔴 DOWN", "Kafka unreachable", 999)

        latency_ms = (time.time() - start) * 1000
        st.session_state.kafka_latency.append(latency_ms)
        st.session_state.kafka_latency = st.session_state.kafka_latency[-30:]

        ts = st.session_state.last_message_ts
        if ts is None:
            return ("🟡 Idle", "Waiting for events", latency_ms)

        gap = time.time() - ts
        if gap < 60:
            heartbeat = "🟢 Active"
        elif gap < 300:
            heartbeat = "🟡 Idle"
        else:
            heartbeat = "🔴 Stale"

        return (heartbeat, f"Last: {int(gap)}s ago", latency_ms)

    status, status_desc, kafka_latency = compute_system_status()

    # Metrics
    total_failures = len(st.session_state.builds)
    all_pr_events = []
    for b in st.session_state.builds.values():
        all_pr_events.extend(b.get("pr", []))

    total_pr = len(all_pr_events)
    merged = len([e for e in all_pr_events if e.get("merged")])
    merge_rate = (merged / total_pr * 100) if total_pr else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("System", status, delta=status_desc)
    m2.metric("Latency", f"{kafka_latency:.1f}ms")
    m3.metric("Merge Rate", f"{merge_rate:.1f}%")
    m4.metric("Builds", total_failures)

    st.divider()

    # Consume message
    msg = consumer.poll(0.5)
    if msg and not msg.error():
        data = json.loads(msg.value().decode("utf-8"))
        st.session_state.last_message_ts = time.time()

        topic = msg.topic()
        build_id = data.get("id") if topic == "ci_failures" else data.get("failure_id")

        if build_id:
            if build_id not in st.session_state.builds:
                st.session_state.builds[build_id] = {
                    "failure": None, "fix": None, "pr": [], "ts": time.time()
                }

            if topic == "ci_failures":
                st.session_state.builds[build_id]["failure"] = data
            elif topic == "ci_ai_fixes":
                st.session_state.builds[build_id]["fix"] = data
            elif topic == "ci_pr_updates":
                st.session_state.builds[build_id]["pr"].append(data)

    # Display builds
    if len(st.session_state.builds) == 0:
        st.info("🎯 Waiting for CI failures...")
    else:
        for build_id, info in sorted(st.session_state.builds.items(), key=lambda x: x[1]["ts"], reverse=True):
            fail = info.get("failure")
            fix = info.get("fix")

            if not fail and not fix:
                continue

            event_repo = None
            if fail:
                event_repo = f"{fail.get('repo_owner')}/{fail.get('repo_name')}"
            elif fix:
                event_repo = f"{fix.get('repo_owner')}/{fix.get('repo_name')}"

            if event_repo != selected_repo:
                continue

            st.markdown(f"## 🧪 Build `{build_id}`")

            c1, c2 = st.columns(2)

            with c1:
                st.subheader("❌ CI Failure")
                if fail:
                    st.markdown(f'<div class="log-box">{fail.get("log","")}</div>', unsafe_allow_html=True)
                    with st.expander("📄 Source Code"):
                        st.code(fail.get("code", ""), language="python")
                else:
                    st.info("⏳ Waiting...")

            with c2:
                st.subheader("🤖 AI Fix")
                if fix:
                    st.info(f"**Root:** {fix.get('root_cause','')}")
                    st.write(fix.get("explanation", ""))
                    with st.expander("🔧 Patch", expanded=True):
                        st.code(fix.get("patch", ""), language="diff")
                    if fix.get("pr_url"):
                        st.success(f"✅ PR: {fix['pr_url']}")
                else:
                    st.warning("⏳ Analyzing...")

            st.subheader("📌 PR Timeline")
            if fix and fix.get("pr_url"):
                st.markdown(f"""
                    <div class="timeline-box status-created">
                        🚀 <strong>PR Created</strong><br>
                        <small>{fix['pr_url']}</small>
                    </div>
                """, unsafe_allow_html=True)

            for ev in info["pr"]:
                if ev.get("merged"):
                    st.markdown('<div class="timeline-box status-merged">✅ <strong>Merged</strong></div>', unsafe_allow_html=True)
                elif ev.get("action") == "closed":
                    st.markdown('<div class="timeline-box status-closed">❌ <strong>Closed</strong></div>', unsafe_allow_html=True)

            st.divider()

    # Auto-refresh
    time.sleep(2)
    st.rerun()

# =============================================================================
# MAIN ROUTER
# =============================================================================
if st.session_state.page == 'home':
    show_home_page()
elif st.session_state.page == 'connect':
    show_connect_page()
elif st.session_state.page == 'dashboard':
    show_dashboard_page()