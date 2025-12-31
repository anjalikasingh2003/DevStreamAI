from google.cloud import firestore
from dotenv import load_dotenv
load_dotenv()

db = firestore.Client()
db.collection("test").document("ping").set({"ok": True})
print("Firestore working!")