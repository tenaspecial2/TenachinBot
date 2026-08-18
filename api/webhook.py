import sys
import os
import json
import asyncio
import logging
from http.server import BaseHTTPRequestHandler

# Add parent directory to path so we can import from main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from supabase import create_client

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Supabase FSM Storage (replaces MemoryStorage)
# ──────────────────────────────────────────────

class SupabaseStorage(BaseStorage):
    """Persistent FSM storage backed by Supabase."""

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        self._client = create_client(url, key) if url and key else None

    def _row_id(self, key: StorageKey) -> dict:
        return {"chat_id": str(key.chat_id), "user_id": str(key.user_id)}

    def _get_row(self, key: StorageKey):
        if not self._client:
            return None
        try:
            res = self._client.table("bot_fsm_states") \
                .select("*") \
                .eq("chat_id", str(key.chat_id)) \
                .eq("user_id", str(key.user_id)) \
                .maybeSingle() \
                .execute()
            return res.data
        except Exception as e:
            logger.error(f"SupabaseStorage get error: {e}")
            return None

    def _upsert_row(self, key: StorageKey, state: str = None, data: dict = None):
        if not self._client:
            return
        try:
            row = {
                "chat_id": str(key.chat_id),
                "user_id": str(key.user_id),
                "state": state,
                "data": json.dumps(data or {}),
            }
            self._client.table("bot_fsm_states").upsert(row).execute()
        except Exception as e:
            logger.error(f"SupabaseStorage upsert error: {e}")

    async def set_state(self, key: StorageKey, state: StateType = None):
        row = self._get_row(key)
        existing_data = json.loads(row["data"]) if row and row.get("data") else {}
        state_str = state.state if hasattr(state, "state") else state
        self._upsert_row(key, state=state_str, data=existing_data)

    async def get_state(self, key: StorageKey) -> str | None:
        row = self._get_row(key)
        return row["state"] if row else None

    async def set_data(self, key: StorageKey, data: dict):
        row = self._get_row(key)
        existing_state = row["state"] if row else None
        self._upsert_row(key, state=existing_state, data=data)

    async def get_data(self, key: StorageKey) -> dict:
        row = self._get_row(key)
        if row and row.get("data"):
            try:
                return json.loads(row["data"])
            except Exception:
                pass
        return {}

    async def close(self):
        pass


# ──────────────────────────────────────────────
# Bot & Dispatcher factory
# ──────────────────────────────────────────────

async def process_telegram_update(body: bytes):
    from main import router, BOT_TOKEN
    from services.supabase_service import init_supabase

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set")
        return

    init_supabase()

    bot = Bot(token=BOT_TOKEN)
    storage = SupabaseStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    update_data = json.loads(body)
    update = Update(**update_data)

    try:
        await dp.process_update(update)
    finally:
        await bot.session.close()


# ──────────────────────────────────────────────
# Vercel Serverless Handler
# ──────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Tenachin Bot webhook is active.")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            asyncio.run(process_telegram_update(body))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"ok":false}')
