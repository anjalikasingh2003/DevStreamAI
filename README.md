# 🚀 DevStream AI  
AI-powered CI/CD Failure Detection, Root-Cause Analysis & Automated PR Fixes

DevStream AI listens to CI/CD failure events, analyzes them using an AI engine, generates patch fixes, and automatically creates pull requests to resolve issues.  
A real-time dashboard shows failure events, analytics, and auto-fix history.

---

## 📦 Features

- 🔍 Real-time CI/CD Failure Detection via Kafka  
- 🧠 AI Failure Analysis (explanation + root cause + patch diff)  
- 🔧 Automated Pull Request Creation  
- 📊 Streamlit Dashboard for monitoring  
- 📣 Slack + Email notifications  
- ⚡ FastAPI backend (optional API layer)  
- 🔐 Fully environment-driven via `.env`

---

## 📥 Installation

```bash
git clone https://github.com/anjalikasingh2003/DevStreamAI.git
cd DevStreamAI
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 📦 requirements.txt

```
fastapi
uvicorn
google-cloud-aiplatform
python-dotenv
confluent-kafka
requests
google-cloud-firestore
google-cloud-core
google-auth
google-auth-oauthlib
```

---

## 🔧 Environment Variables (`.env`)

Create a `.env` file in the project root:

```
# Kafka
CONFLUENT_BOOTSTRAP=
KAFKA_API_KEY=
KAFKA_API_SECRET=

# GitHub
GITHUB_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=
GITHUB_WEBHOOK_SECRET=

# Slack
SLACK_WEBHOOK_URL=

# Email Notifications
SMTP_EMAIL=
SMTP_PASSWORD=
SMTP_SERVER=
SMTP_PORT=587
```

> ⚠️ IMPORTANT: Do NOT commit `.env` to GitHub.

---

## ▶️ Running DevStream AI

You must start **two terminals**:

---

### **Terminal 1 — Start CI/CD Failure Consumer (Kafka Listener)**

```bash
python3 -m backend.streaming.consumer
```

This:

- Reads CI/CD failure events  
- Sends them to AI engine  
- Generates explanation + root cause  
- Produces patch diff  
- Optionally creates a GitHub PR  

---

### **Terminal 2 — Start the Dashboard**

```bash
cd backend/dashboard
streamlit run dashboard.py
```

Open the dashboard at:  
👉 http://localhost:8501

---


## 📊 Dashboard Features

- Live CI failure stream  
- AI-generated explanations  
- Patch diffs  
- Auto PR logs  
- PR merge success-rate sparkline  
- Premium UI styling  

---

## 🤝 Contributing

Pull requests are welcome.

---

## 🛡️ License

MIT

