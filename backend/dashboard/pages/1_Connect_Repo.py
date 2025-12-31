from datetime import datetime
import streamlit as st
import requests
import os
import json
from google.cloud import firestore
db = firestore.Client()
API_URL = "https://devstream-backend-176657413002.us-central1.run.app"
REG_FILE = "registered_repos.json"

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Connect Repository · DevStreamAI",
    page_icon="🔗",
    layout="wide"
)

# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------
st.markdown("""
<style>
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
    
    .step-number {
        background: #667eea;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 50%;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    
    .code-block {
        background: #282c34;
        color: #abb2bf;
        padding: 1rem;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# INPUT SECTION
# ---------------------------------------------------------
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

submit = st.button("🚀 Connect Repository", type="primary", use_container_width=True)

# ---------------------------------------------------------
# HELPER FUNCTION TO SAVE REPO
# ---------------------------------------------------------
def save_registered_repo(repo_name):
    """Save repository to local JSON file"""
    repos = []
    if os.path.exists(REG_FILE):
        with open(REG_FILE, 'r') as f:
            repos = json.load(f)
    
    if repo_name not in repos:
        repos.append(repo_name)
        with open(REG_FILE, 'w') as f:
            json.dump(repos, f, indent=2)

# ---------------------------------------------------------
# ON SUBMIT
# ---------------------------------------------------------
if submit:
    if not repo_url.strip():
        st.error("❗ Please provide a valid GitHub repository URL.")
    else:
        with st.spinner("🔄 Registering your repository with DevStreamAI..."):
            try:
                resp = requests.post(
                    f"{API_URL}/api/register_repo",
                    json={"repo_url": repo_url},
                    timeout=10
                )
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Please try again.")
                st.stop()
            except Exception as e:
                st.error(f"❌ API connection failed: {e}")
                st.stop()

        if resp.status_code != 200:
            st.error(f"❌ Backend Error (Status {resp.status_code}):\n\n{resp.text}")
            st.stop()

        try:
            data = resp.json()
        except:
            st.error("❌ Invalid response from backend")
            st.stop()

        if data.get("status") != "success":
            st.error(f"❌ Error: {data.get('message', 'Unknown error')}")
            st.stop()

        # Save to registered repos
        repo_full_name = data.get('repo')
        if repo_full_name:
            doc_id = repo_full_name.replace("/", "_")  # owner_repo
            db.collection("repos").document(doc_id).set({
                "full_name": repo_full_name,
                "added_at": datetime.now().isoformat()
            })

        # ---------------------------------------------------------
        # SUCCESS STATE
        # ---------------------------------------------------------
        st.balloons()
        
        st.markdown(f"""
        <div class="success-box">
            <h3>✅ Repository Successfully Connected!</h3>
            <p><strong>Repository:</strong> {repo_full_name}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ---------------------------------------------------------
        # STEP 2: CI WORKFLOW
        # ---------------------------------------------------------
        st.markdown("## ⚙️ Step 2: Add CI Workflow")
        
        st.markdown("""
        Copy the workflow file below and save it to your repository:
        
        **File Path:** `.github/workflows/devstream.yml`
        """)

        st.code(data.get("yaml_template", ""), language="yaml")

        # ---------------------------------------------------------
        # STEP 3: ADD SECRET
        # ---------------------------------------------------------
        st.markdown("## 🔐 Step 3: Configure GitHub Secret")
        
        st.markdown("""
        <div class="instruction-box">
            <p><span class="step-number">1</span> Go to your repository on GitHub</p>
            <p><span class="step-number">2</span> Navigate to: <strong>Settings → Secrets and variables → Actions</strong></p>
            <p><span class="step-number">3</span> Click <strong>"New repository secret"</strong></p>
            <p><span class="step-number">4</span> Use the following values:</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input(
                "Secret Name",
                value="DEVSTREAM_WEBHOOK",
                disabled=True,
                key="secret_name"
            )
        
        with col2:
            webhook_url = "https://devstream-backend-176657413002.us-central1.run.app/api/send_ci_failure"
            st.text_input(
                "Secret Value",
                value=webhook_url,
                disabled=True,
                key="secret_value"
            )

        # ---------------------------------------------------------
        # STEP 4: TEST IT
        # ---------------------------------------------------------
        st.markdown("## 🧪 Step 4: Test the Integration")
        
        st.markdown("""
        <div class="instruction-box">
            <p><strong>To test DevStreamAI:</strong></p>
            <ol>
                <li>Commit the workflow file to your repository</li>
                <li>Push a commit that causes a CI failure</li>
                <li>Watch the magic happen in the Dashboard! 🎉</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ---------------------------------------------------------
        # NAVIGATION TO DASHBOARD
        # ---------------------------------------------------------
        st.markdown("## 🎉 All Set! Ready to Monitor")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("📊 Go to Dashboard →", type="primary", use_container_width=True):
                st.switch_page("pages/2_dashboard.py")

else:
    # Show example when not submitted
    st.markdown("---")
    st.markdown("### 📖 How It Works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **1. Connect**
        
        Enter your GitHub repository URL and click connect.
        """)
    
    with col2:
        st.markdown("""
        **2. Configure**
        
        Add the CI workflow and webhook secret to your repo.
        """)
    
    with col3:
        st.markdown("""
        **3. Monitor**
        
        Watch AI-powered fixes appear in real-time!
        """)

st.markdown("---")
st.caption("DevStreamAI · Powered by Confluent Kafka & Claude AI")