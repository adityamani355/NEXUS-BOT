import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).resolve().parent / "nexusbot.sqlite3")))

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(owner_id):
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
          updated_at TEXT NOT NULL, dm_started INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE) WHERE username IS NOT NULL;
        CREATE TABLE IF NOT EXISTS group_users(
          chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT, first_name TEXT,
          updated_at TEXT NOT NULL, PRIMARY KEY(chat_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS filters(
          keyword TEXT PRIMARY KEY COLLATE NOCASE, response TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS media_filters(
          media_key TEXT PRIMARY KEY, media_type TEXT NOT NULL, file_unique_id TEXT NOT NULL,
          response TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          actor_id INTEGER NOT NULL DEFAULT 0, action TEXT NOT NULL,
          target_id INTEGER, details TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS group_scores(
          chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT, first_name TEXT,
          total_points INTEGER NOT NULL DEFAULT 0, aura_points INTEGER NOT NULL DEFAULT 0,
          aura_protect_until REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
          PRIMARY KEY(chat_id,user_id)
        );
        """)
        # Safe migration for databases created by earlier Nexus Bot versions.
        user_columns = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
        if "dm_started" not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN dm_started INTEGER NOT NULL DEFAULT 0")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('owner_id',?)", (str(owner_id),))
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('auto_approve','0')")

def upsert_user(user_id, username, first_name):
    username = username.lstrip("@") if username else None
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        # Telegram usernames can be reassigned; avoid a stale unique-index collision.
        if username:
            c.execute("UPDATE users SET username=NULL WHERE username=? COLLATE NOCASE AND user_id<>?", (username, int(user_id)))
        c.execute("""INSERT INTO users(user_id,username,first_name,updated_at) VALUES(?,?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, updated_at=excluded.updated_at""",
          (int(user_id), username, first_name or "", now))

def upsert_group_user(chat_id, user_id, username, first_name):
    username = username.lstrip("@") if username else None
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("""INSERT INTO group_users(chat_id,user_id,username,first_name,updated_at) VALUES(?,?,?,?,?)
          ON CONFLICT(chat_id,user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, updated_at=excluded.updated_at""",
          (int(chat_id), int(user_id), username, first_name or "", now))

def list_group_users(chat_id, limit=500):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT user_id,username,first_name FROM group_users WHERE chat_id=? ORDER BY updated_at DESC LIMIT ?", (int(chat_id), int(limit))).fetchall()]

def get_user_by_username(username):
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username.lstrip("@"),)).fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id):
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return dict(row) if row else None

def add_log(actor_id, action, target_id=None, details=""):
    with connect() as c:
        c.execute("INSERT INTO logs(created_at,actor_id,action,target_id,details) VALUES(?,?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(timespec="seconds"), int(actor_id or 0), action, target_id, str(details)[:1000]))

def is_owner(user_id):
    return int(user_id) == get_owner_id()

def get_owner_id():
    with connect() as c:
        row = c.execute("SELECT value FROM settings WHERE key='owner_id'").fetchone()
        return int(row["value"]) if row else 0

def get_filters():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT keyword,response FROM filters ORDER BY keyword LIMIT 200").fetchall()]

def add_filter(keyword, response):
    with connect() as c:
        c.execute("INSERT INTO filters(keyword,response) VALUES(?,?) ON CONFLICT(keyword) DO UPDATE SET response=excluded.response",
                  (keyword.strip().lower()[:100], response.strip()[:500]))

def remove_filter(keyword):
    with connect() as c:
        c.execute("DELETE FROM filters WHERE keyword=? COLLATE NOCASE", (keyword,))

def add_media_filter(media_type, file_unique_id, response):
    key = f"{media_type}:{file_unique_id}"
    with connect() as c:
        c.execute("INSERT INTO media_filters(media_key,media_type,file_unique_id,response,created_at) VALUES(?,?,?,?,?) "
                  "ON CONFLICT(media_key) DO UPDATE SET response=excluded.response",
                  (key, media_type, file_unique_id, response.strip()[:500], datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return key

def get_media_filters():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT media_key,media_type,file_unique_id,response,created_at FROM media_filters ORDER BY created_at DESC LIMIT 200").fetchall()]

def get_media_filter(media_type, file_unique_id):
    key = f"{media_type}:{file_unique_id}"
    with connect() as c:
        row = c.execute("SELECT * FROM media_filters WHERE media_key=?", (key,)).fetchone()
        return dict(row) if row else None

def remove_media_filter(media_key):
    with connect() as c:
        c.execute("DELETE FROM media_filters WHERE media_key=?", (media_key,))

def list_users(limit=50):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT user_id,username FROM users ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()]

def list_logs(limit=30):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT created_at,actor_id,action,target_id,details FROM logs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()]

def get_settings():
    with connect() as c:
        return {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings").fetchall()}

def set_setting(key, value):
    with connect() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def get_stats():
    with connect() as c:
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        filters_count = c.execute("SELECT COUNT(*) n FROM filters").fetchone()["n"]
        media_count = c.execute("SELECT COUNT(*) n FROM media_filters").fetchone()["n"]
        logs = c.execute("SELECT COUNT(*) n FROM logs").fetchone()["n"]
        return {"users": users, "filters": filters_count + media_count, "media_filters": media_count, "logs": logs}


def mark_dm_started(user_id):
    """Record that the user explicitly opened the bot in a private chat."""
    with connect() as c:
        c.execute("UPDATE users SET dm_started=1 WHERE user_id=?", (int(user_id),))


def has_dm_started(user_id):
    with connect() as c:
        row = c.execute("SELECT dm_started FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return bool(row and row["dm_started"])


def ensure_score(chat_id, user_id, username=None, first_name=None):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as c:
        c.execute("""INSERT INTO group_scores(chat_id,user_id,username,first_name,updated_at) VALUES(?,?,?,?,?)
          ON CONFLICT(chat_id,user_id) DO UPDATE SET username=COALESCE(excluded.username,group_scores.username),
          first_name=COALESCE(excluded.first_name,group_scores.first_name), updated_at=excluded.updated_at""",
          (int(chat_id), int(user_id), username.lstrip("@") if username else None, first_name or "", now))

def adjust_score(chat_id, user_id, username, first_name, total_delta=0, aura_delta=0):
    ensure_score(chat_id, user_id, username, first_name)
    with connect() as c:
        row = c.execute("SELECT aura_protect_until FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        if aura_delta < 0 and row and float(row["aura_protect_until"] or 0) > __import__("time").time():
            aura_delta = 0
        c.execute("UPDATE group_scores SET total_points=MAX(0,total_points+?), aura_points=MAX(0,aura_points+?), updated_at=? WHERE chat_id=? AND user_id=?",
          (int(total_delta), int(aura_delta), datetime.now(timezone.utc).isoformat(timespec="seconds"), int(chat_id), int(user_id)))
    return get_score(chat_id, user_id)

def get_score(chat_id, user_id):
    with connect() as c:
        row = c.execute("SELECT * FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        return dict(row) if row else None

def leaderboard(chat_id, column="total_points", limit=10):
    if column not in ("total_points", "aura_points"):
        column = "total_points"
    with connect() as c:
        return [dict(r) for r in c.execute(f"SELECT * FROM group_scores WHERE chat_id=? ORDER BY {column} DESC, updated_at ASC LIMIT ?", (int(chat_id), int(limit))).fetchall()]

def buy_aura_protection(chat_id, user_id, username, first_name, days, cost):
    ensure_score(chat_id, user_id, username, first_name)
    import time
    now = time.time()
    with connect() as c:
        row = c.execute("SELECT total_points,aura_protect_until FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        if int(row["total_points"]) < int(cost):
            return False, dict(row)
        until = max(now, float(row["aura_protect_until"] or 0)) + int(days) * 86400
        c.execute("UPDATE group_scores SET total_points=total_points-?, aura_protect_until=?, updated_at=? WHERE chat_id=? AND user_id=?",
          (int(cost), until, datetime.now(timezone.utc).isoformat(timespec="seconds"), int(chat_id), int(user_id)))
        fresh = c.execute("SELECT * FROM group_scores WHERE chat_id=? AND user_id=?", (int(chat_id), int(user_id))).fetchone()
        return True, dict(fresh)
