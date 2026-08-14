import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = None


def init_supabase():
    """Initialize the Supabase client using the service role key."""
    global supabase
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.warning("⚠️ SUPABASE_URL or SUPABASE_SERVICE_KEY not set. Running without Supabase.")
        return
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ Supabase connected successfully.")
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {e}")


# ─────────────────────────────────────────────
# TRANSACTIONS (bot-side payment records)
# ─────────────────────────────────────────────

def record_transaction_supabase(doctor_name: str, item_type: str, item_title: str, price: float, user_id: int):
    """Record a payment transaction into Supabase bot_transactions table."""
    if not supabase:
        return
    try:
        supabase.table("bot_transactions").insert({
            "doctor_name": doctor_name,
            "item_type": item_type,
            "item_title": item_title,
            "price": price,
            "telegram_user_id": str(user_id),
        }).execute()
        logger.info(f"✅ Transaction recorded for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to record transaction: {e}")


def get_all_transactions():
    """Fetch all transactions for admin report."""
    if not supabase:
        return []
    try:
        res = supabase.table("bot_transactions").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"❌ Failed to fetch transactions: {e}")
        return []


# ─────────────────────────────────────────────
# CONSULTATIONS (read from website data)
# ─────────────────────────────────────────────

def get_approved_consultations():
    """Fetch approved consultations from the website's Supabase table."""
    if not supabase:
        return []
    try:
        res = supabase.table("consultations").select(
            "id, patient_id, doctor_id, plan, amount, status"
        ).eq("status", "approved").execute()
        return res.data or []
    except Exception as e:
        logger.error(f"❌ Failed to fetch consultations: {e}")
        return []


def approve_consultation(consultation_id: str, admin_note: str = "Approved via bot"):
    """Approve a consultation from the bot (admin action)."""
    if not supabase:
        return False
    try:
        supabase.table("consultations").update({
            "status": "approved",
            "admin_note": admin_note,
        }).eq("id", consultation_id).execute()
        logger.info(f"✅ Consultation {consultation_id} approved via bot")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to approve consultation: {e}")
        return False


def decline_consultation(consultation_id: str, admin_note: str = "Declined via bot"):
    """Decline a consultation from the bot (admin action)."""
    if not supabase:
        return False
    try:
        supabase.table("consultations").update({
            "status": "declined",
            "admin_note": admin_note,
        }).eq("id", consultation_id).execute()
        logger.info(f"✅ Consultation {consultation_id} declined via bot")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to decline consultation: {e}")
        return False


# ─────────────────────────────────────────────
# NOTIFICATIONS (send to website users)
# ─────────────────────────────────────────────

def send_notification_supabase(user_id: str, title: str, body: str):
    """Insert a notification for a website user."""
    if not supabase:
        return
    try:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "body": body,
        }).execute()
        logger.info(f"✅ Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send notification: {e}")
