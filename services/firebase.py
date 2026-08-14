import os
import firebase_admin
from firebase_admin import credentials, firestore
from config import settings

db = None


def init_firebase():
    """Initialize Firebase Admin SDK."""
    global db
    if not firebase_admin._apps:
        cred_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase initialized successfully.")
        else:
            print(f"⚠️ Warning: {cred_path} not found. Running without Firebase.")


async def save_document(collection: str, doc_id: str, data: dict):
    """Save or overwrite a document in Firestore."""
    if db:
        db.collection(collection).document(str(doc_id)).set(data, merge=True)


async def update_document(collection: str, doc_id: str, data: dict):
    """Update fields in an existing Firestore document."""
    if db:
        db.collection(collection).document(str(doc_id)).update(data)


async def get_document(collection: str, doc_id: str) -> dict:
    """Retrieve a document from Firestore."""
    if db:
        doc = db.collection(collection).document(str(doc_id)).get()
        if doc.exists:
            return doc.to_dict()
    return {}