import streamlit as st

st.set_page_config(page_title="DevStreamAI", page_icon="🚀", layout="wide")

# -------------------------
# Custom Navigation (no page_link)
# -------------------------
params = st.experimental_get_query_params()
page = params.get("page", ["home"])[0]

if st.button("🔗 Connect Repository"):
    st.experimental_set_query_params(page="connect")

if st.button("📊 Open Dashboard"):
    st.experimental_set_query_params(page="dashboard")

# -------------------------
# Landing Page UI
# -------------------------
if page == "home":
    st.markdown("""
    <h1 style='text-align:center;'>🚀 DevStreamAI</h1>
    <p style='text-align:center; color:#666; font-size:18px;'>
        AI-powered CI/CD debugging with real-time auto-fix PR generation
    </p>
    <br><br>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔗 Connect Your Repository", key="connect_btn", use_container_width=True):
            st.experimental_set_query_params(page="connect")

    with col2:
        if st.button("📊 Open Dashboard", key="dash_btn", use_container_width=True):
            st.experimental_set_query_params(page="dashboard")

elif page == "connect":
    st.write("Loading Connect Repo page...")
    st.switch_page("pages/1_connect_repo.py")

elif page == "dashboard":
    st.write("Loading Dashboard...")
    st.switch_page("pages/2_dashboard.py")
