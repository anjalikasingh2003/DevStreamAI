
import streamlit as st
import requests
import os

API_URL = "https://devstream-backend-176657413002.us-central1.run.app"

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(page_title="Connect Repository · DevStreamAI", page_icon="🔗", layout="wide")
import streamlit as st

st.title("🔗 Connect Your GitHub Repository")

st.markdown("""
Use DevStreamAI to automatically:
- Run CI on your repository  
- Detect failures in real-time  
- Auto-analyze failures  
- Auto-generate PR fixes  
- Track PR timeline  
""")

st.markdown("---")

# ---------------------------------------------------------
# INPUT BOX
# ---------------------------------------------------------
repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/<owner>/<repo>",
    help="Paste your GitHub repo link. Example: https://github.com/anjalikasingh2003/Dummy"
)

submit = st.button("🚀 Connect Repository", type="primary")

# ---------------------------------------------------------
# ON SUBMIT
# ---------------------------------------------------------
if submit:
    if not repo_url.strip():
        st.error("❗ Please provide a GitHub repository URL.")
    else:
        with st.spinner("Registering your repository with DevStreamAI..."):
            try:
                resp = requests.post(f"{API_URL}/api/register_repo", json={"repo_url": repo_url})
            except Exception as e:
                st.error(f"API connection failed: {e}")
                st.stop()

        if resp.status_code != 200:
            st.error(f"❌ Error from backend:\n{resp.text}")
            st.stop()

        data = resp.json()

        if data.get("status") != "success":
            st.error(f"❌ Error: {data.get('message')}")
            st.stop()

        st.success(f"Repository Connected: **{data['repo']}**")

        st.markdown("### 📄 Generated CI Workflow (Copy this to `.github/workflows/devstream.yml`):")
        st.code(data["yaml_template"], language="yaml")

        st.info("""
            ### Next Steps  
            1. Go to: **GitHub → Settings → Secrets → Actions**  
            2. Add secret: **DEVSTREAM_WEBHOOK**  
            3. Value = your backend endpoint:  
                https://devstream-backend-176657413002.us-central1.run.app/api/send_ci_failure
            4. Commit the YAML file  
            5. Push a failing commit and watch auto-fixes in Dashboard  
            """)

        # Save repo selection for dashboard filtering
        st.session_state["connected_repo"] = data["repo"]

        # 🚀 Show button to go to dashboard
        st.markdown("### 🚀 Next: Open Dashboard")
        # if st.button("📊 Go to Dashboard"):
        #     st.experimental_set_query_params(page="dashboard")


st.markdown("---")
st.caption("DevStreamAI · Confluent x Google Cloud Hackathon")

