import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = os.getenv("DATABASE_PATH", "mindmate.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1, dklen=64).hex()
    return f"{salt}:{derived}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split(":")
    if len(parts) != 2:
        return False
    salt, key_hex = parts
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1, dklen=64).hex()
    return secrets.compare_digest(key_hex, derived)


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          university TEXT DEFAULT 'State University',
          major TEXT DEFAULT 'Computer Applications (MCA)',
          year_of_study TEXT DEFAULT 'Year 2',
          community_alias TEXT NOT NULL,
          is_demo INTEGER DEFAULT 0,
          privacy_anonymous_community INTEGER DEFAULT 1,
          privacy_include_insights INTEGER DEFAULT 1,
          privacy_retention_days INTEGER DEFAULT 90,
          created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mood_checkins (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          mood TEXT NOT NULL,
          stress_level INTEGER NOT NULL,
          energy_level INTEGER NOT NULL,
          note TEXT DEFAULT '',
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS study_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          subject TEXT NOT NULL,
          title TEXT NOT NULL,
          description TEXT DEFAULT '',
          deadline TEXT NOT NULL,
          priority TEXT NOT NULL DEFAULT 'medium',
          scheduled_slot TEXT DEFAULT 'Morning (09:00 - 11:00)',
          completed INTEGER DEFAULT 0,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS focus_sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          mode TEXT NOT NULL DEFAULT 'focus',
          duration_minutes INTEGER NOT NULL,
          subject TEXT DEFAULT 'General Study',
          completed_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          role TEXT NOT NULL,
          content TEXT NOT NULL,
          crisis_flagged INTEGER DEFAULT 0,
          source TEXT DEFAULT 'fallback',
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS community_posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          author_alias TEXT NOT NULL,
          category TEXT NOT NULL,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          reported INTEGER DEFAULT 0,
          report_reason TEXT DEFAULT '',
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS community_comments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          post_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          author_alias TEXT NOT NULL,
          content TEXT NOT NULL,
          reported INTEGER DEFAULT 0,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS community_reactions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          post_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          reaction_type TEXT NOT NULL,
          created_at TEXT DEFAULT (datetime('now')),
          UNIQUE(post_id, user_id, reaction_type),
          FOREIGN KEY (post_id) REFERENCES community_posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS counsellor_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          counsellor_name TEXT NOT NULL,
          preferred_slot TEXT NOT NULL,
          topic TEXT NOT NULL,
          consent_given INTEGER NOT NULL DEFAULT 1,
          status TEXT NOT NULL DEFAULT 'Requested',
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    existing = cur.execute("SELECT id FROM users WHERE email = ?", ("maya.patel@campus.edu",)).fetchone()
    if not existing:
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, university, major, year_of_study, community_alias, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                "Maya Patel",
                "maya.patel@campus.edu",
                hash_password("MindMate2026!"),
                "Crestwood Institute of Technology",
                "Master of Computer Applications (MCA)",
                "Final Year",
                "Calm Maple #108",
            ),
        )
        demo_id = cur.lastrowid

        now = datetime.now(timezone.utc)
        mood_seed = [
            (7, "Stressed", 8, 4, "Two project milestones due in the same week."),
            (6, "Anxious", 7, 5, "Worried about upcoming seminar presentation."),
            (5, "Neutral", 5, 6, "Broke the assignment into smaller tasks, felt steadier."),
            (4, "Calm", 4, 7, "Walked outside for 20 minutes between lectures."),
            (3, "Happy", 3, 8, "Finished database schema ahead of schedule!"),
            (2, "Calm", 4, 7, "Good sleep last night and steady study pace."),
            (1, "Stressed", 6, 5, "Late evening debugging session made me tired."),
            (0, "Calm", 4, 7, "Morning breathing exercise helped me start focused."),
        ]
        for days, mood, stress, energy, note in mood_seed:
            ts = (now - timedelta(days=days)).isoformat()
            cur.execute(
                "INSERT INTO mood_checkins (user_id, mood, stress_level, energy_level, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (demo_id, mood, stress, energy, note, ts),
            )

        cur.execute(
            "INSERT INTO study_tasks (user_id, subject, title, description, deadline, priority, scheduled_slot, completed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                demo_id,
                "Algorithms & Complexity",
                "Dynamic Programming Problem Set 4",
                "Complete memoization proofs and time-complexity analysis.",
                (now + timedelta(days=1)).date().isoformat(),
                "high",
                "Morning (09:00 - 11:00)",
                0,
            ),
        )
        cur.execute(
            "INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source) VALUES (?, 'assistant', ?, 0, 'fallback')",
            (
                demo_id,
                "Hi Maya, I'm MindMate—your private wellbeing companion. How is your day feeling so far?",
            ),
        )
    conn.commit()
    conn.close()
