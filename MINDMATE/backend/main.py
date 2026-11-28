import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import get_connection, hash_password, init_db, verify_password

load_dotenv()
init_db()

app = FastAPI(title="MINDMATE Student Wellbeing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
ALLOWED_MOODS = {"Happy", "Calm", "Neutral", "Stressed", "Sad", "Anxious"}
MOOD_SCORES = {"Happy": 5, "Calm": 4, "Neutral": 3, "Stressed": 2, "Anxious": 2, "Sad": 1}
CRISIS_REGEX = re.compile(
    r"\b(kill myself|end my life|want to die|suicide|suicidal|hurt myself|self[- ]harm|cut myself|no reason to live|better off dead|overdose)\b",
    re.IGNORECASE,
)


def create_token(user_id: int, email: str) -> str:
    payload = {"userId": user_id, "email": email, "exp": int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp() * 1000)}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac.new(SESSION_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return f"{encoded}.{sig}"


def verify_token(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = authorization[7:].strip()
    parts = token.split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    encoded, sig = parts
    expected = base64.urlsafe_b64encode(hmac.new(SESSION_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    if not secrets.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="Invalid session signature.")
    padded = encoded + "=" * (-len(encoded) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded).decode())
    if payload.get("exp", 0) < int(datetime.now(timezone.utc).timestamp() * 1000):
        raise HTTPException(status_code=401, detail="Session expired.")
    return payload


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=4, max_length=120)
    password: str = Field(min_length=6, max_length=120)
    university: str = "State University"
    major: str = "General Studies"
    year_of_study: str = "Year 1"


class LoginInput(BaseModel):
    email: str
    password: str


class MoodInput(BaseModel):
    mood: str
    stress_level: int = Field(ge=1, le=10)
    energy_level: int = Field(ge=1, le=10)
    note: str = ""


class TaskInput(BaseModel):
    subject: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = ""
    deadline: str = ""
    priority: str = "medium"
    scheduled_slot: str = "Morning (09:00 - 11:00)"
    completed: Optional[bool] = False


class FocusInput(BaseModel):
    mode: str = "focus"
    duration_minutes: int = Field(ge=1, le=120)
    subject: str = "General Study"


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=1500)


class PostInput(BaseModel):
    category: str = "Academic Stress"
    title: str = Field(min_length=3, max_length=120)
    content: str = Field(min_length=8, max_length=1000)


class ReactInput(BaseModel):
    reaction_type: str


class CommentInput(BaseModel):
    content: str = Field(min_length=2, max_length=500)


class ReportInput(BaseModel):
    reason: str = "Flagged for review"


class PrivacyInput(BaseModel):
    privacy_anonymous_community: bool = True
    privacy_include_insights: bool = True
    privacy_retention_days: int = 90


class SupportRequestInput(BaseModel):
    counsellor_name: str
    preferred_slot: str
    topic: str = "General wellbeing check-in"
    consent_given: bool


def safe_user(conn, user_id: int) -> dict:
    row = conn.execute(
        """
        SELECT id, name, email, university, major, year_of_study, community_alias,
               is_demo, privacy_anonymous_community, privacy_include_insights,
               privacy_retention_days, created_at
        FROM users WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    return dict(row) if row else {}


@app.post("/api/auth/register", status_code=201)
def register(data: RegisterInput):
    conn = get_connection()
    email = data.email.strip().lower()
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email already registered.")
    alias = f"Calm Cedar #{100 + (sum(ord(c) for c in email) % 899)}"
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, university, major, year_of_study, community_alias) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data.name.strip(), email, hash_password(data.password), data.university, data.major, data.year_of_study, alias),
    )
    user_id = cur.lastrowid
    conn.commit()
    user = safe_user(conn, user_id)
    conn.close()
    return {"token": create_token(user_id, email), "user": user}


@app.post("/api/auth/login")
def login(data: LoginInput):
    conn = get_connection()
    email = data.email.strip().lower()
    row = conn.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(data.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    user = safe_user(conn, row["id"])
    conn.close()
    return {"token": create_token(row["id"], row["email"]), "user": user}


@app.post("/api/auth/demo")
def demo_login():
    conn = get_connection()
    row = conn.execute("SELECT id, email FROM users WHERE email = ?", ("maya.patel@campus.edu",)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=500, detail="Demo account unavailable.")
    user = safe_user(conn, row["id"])
    conn.close()
    return {"token": create_token(row["id"], row["email"]), "user": user}


@app.get("/api/auth/me")
def me(payload: dict = Depends(verify_token)):
    conn = get_connection()
    user = safe_user(conn, payload["userId"])
    conn.close()
    return {"user": user}


@app.get("/api/moods")
def get_moods(payload: dict = Depends(verify_token)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, mood, stress_level, energy_level, note, created_at FROM mood_checkins WHERE user_id = ? ORDER BY datetime(created_at) DESC, id DESC",
        (payload["userId"],),
    ).fetchall()
    conn.close()
    return {"checkins": [dict(r) for r in rows]}


@app.post("/api/moods", status_code=201)
def add_mood(data: MoodInput, payload: dict = Depends(verify_token)):
    if data.mood not in ALLOWED_MOODS:
        raise HTTPException(status_code=400, detail="Invalid mood option.")
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO mood_checkins (user_id, mood, stress_level, energy_level, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (payload["userId"], data.mood, data.stress_level, data.energy_level, data.note[:500], now),
    )
    row = dict(conn.execute("SELECT id, mood, stress_level, energy_level, note, created_at FROM mood_checkins WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.commit()
    conn.close()
    return {"checkin": row}


@app.delete("/api/moods/{checkin_id}")
def delete_mood(checkin_id: int, payload: dict = Depends(verify_token)):
    conn = get_connection()
    cur = conn.execute("DELETE FROM mood_checkins WHERE id = ? AND user_id = ?", (checkin_id, payload["userId"]))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Mood check-in not found.")
    return {"deleted": True}


@app.get("/api/tasks")
def get_tasks(payload: dict = Depends(verify_token)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, subject, title, description, deadline, priority, scheduled_slot, completed, created_at FROM study_tasks WHERE user_id = ? ORDER BY completed ASC, deadline ASC",
        (payload["userId"],),
    ).fetchall()
    conn.close()
    return {"tasks": [dict(r) for r in rows]}


@app.post("/api/tasks", status_code=201)
def add_task(data: TaskInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    deadline = data.deadline or datetime.now(timezone.utc).date().isoformat()
    cur = conn.execute(
        "INSERT INTO study_tasks (user_id, subject, title, description, deadline, priority, scheduled_slot) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (payload["userId"], data.subject.strip(), data.title.strip(), data.description.strip(), deadline, data.priority, data.scheduled_slot),
    )
    row = dict(conn.execute("SELECT * FROM study_tasks WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.commit()
    conn.close()
    return {"task": row}


@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, data: dict, payload: dict = Depends(verify_token)):
    conn = get_connection()
    existing = conn.execute("SELECT * FROM study_tasks WHERE id = ? AND user_id = ?", (task_id, payload["userId"])).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found.")
    conn.execute(
        "UPDATE study_tasks SET subject = ?, title = ?, description = ?, deadline = ?, priority = ?, scheduled_slot = ?, completed = ? WHERE id = ? AND user_id = ?",
        (
            data.get("subject", existing["subject"]),
            data.get("title", existing["title"]),
            data.get("description", existing["description"]),
            data.get("deadline", existing["deadline"]),
            data.get("priority", existing["priority"]),
            data.get("scheduled_slot", existing["scheduled_slot"]),
            1 if data.get("completed", existing["completed"]) else 0,
            task_id,
            payload["userId"],
        ),
    )
    row = dict(conn.execute("SELECT * FROM study_tasks WHERE id = ?", (task_id,)).fetchone())
    conn.commit()
    conn.close()
    return {"task": row}


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, payload: dict = Depends(verify_token)):
    conn = get_connection()
    cur = conn.execute("DELETE FROM study_tasks WHERE id = ? AND user_id = ?", (task_id, payload["userId"]))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"deleted": True}


@app.get("/api/focus")
def get_focus(payload: dict = Depends(verify_token)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, mode, duration_minutes, subject, completed_at FROM focus_sessions WHERE user_id = ? ORDER BY datetime(completed_at) DESC LIMIT 30",
        (payload["userId"],),
    ).fetchall()
    conn.close()
    return {"sessions": [dict(r) for r in rows]}


@app.post("/api/focus", status_code=201)
def add_focus(data: FocusInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO focus_sessions (user_id, mode, duration_minutes, subject, completed_at) VALUES (?, ?, ?, ?, ?)",
        (payload["userId"], data.mode, data.duration_minutes, data.subject, now),
    )
    row = dict(conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.commit()
    conn.close()
    return {"session": row}


@app.get("/api/chat")
def get_chat(payload: dict = Depends(verify_token)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, role, content, crisis_flagged, source, created_at FROM chat_messages WHERE user_id = ? ORDER BY id ASC",
        (payload["userId"],),
    ).fetchall()
    conn.close()
    return {"messages": [dict(r) for r in rows]}


@app.post("/api/chat", status_code=201)
def send_chat(data: ChatInput, payload: dict = Depends(verify_token)):
    msg_text = data.message.strip()
    crisis = bool(CRISIS_REGEX.search(msg_text))
    source = "fallback"

    if crisis:
        reply_text = (
            "I'm really glad you reached out, and I want to make sure you are safe right now. "
            "Please call or text 988 (US/Canada) or 112/911 for immediate local emergency help, "
            "or contact a trusted person or campus support office right away."
        )
    else:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        reply_text = ""
        if api_key and api_key != "MY_GEMINI_API_KEY":
            try:
                from google import genai

                client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(
                    model="gemini-4-hydrogen",
                    contents=f"You are MindMate, an empathetic, non-diagnostic student wellbeing companion. Respond concisely and supportively to: {msg_text}",
                )
                if resp.text:
                    reply_text = resp.text.strip()
                    source = "gemini"
            except Exception:
                reply_text = ""

        if not reply_text:
            reply_text = (
                "Thank you for sharing what's on your mind. When academic pressure builds up, "
                "try breaking your next task into one 25-minute Pomodoro block and taking a 5-minute breathing pause right after."
            )

    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    u_cur = conn.execute(
        "INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source, created_at) VALUES (?, 'user', ?, ?, 'user', ?)",
        (payload["userId"], msg_text, 1 if crisis else 0, now),
    )
    a_cur = conn.execute(
        "INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source, created_at) VALUES (?, 'assistant', ?, ?, ?, ?)",
        (payload["userId"], reply_text, 1 if crisis else 0, source, now),
    )
    user_msg = dict(conn.execute("SELECT * FROM chat_messages WHERE id = ?", (u_cur.lastrowid,)).fetchone())
    ai_msg = dict(conn.execute("SELECT * FROM chat_messages WHERE id = ?", (a_cur.lastrowid,)).fetchone())
    conn.commit()
    conn.close()
    return {"userMessage": user_msg, "assistantMessage": ai_msg, "crisisFlagged": crisis}


@app.delete("/api/chat")
def clear_chat(payload: dict = Depends(verify_token)):
    conn = get_connection()
    conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (payload["userId"],))
    conn.commit()
    conn.close()
    return {"cleared": True}


@app.get("/api/analytics")
def get_analytics(payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    checkins = [dict(r) for r in conn.execute("SELECT mood, stress_level, energy_level, created_at FROM mood_checkins WHERE user_id = ? ORDER BY datetime(created_at) ASC", (uid,)).fetchall()]
    tasks = [dict(r) for r in conn.execute("SELECT priority, completed FROM study_tasks WHERE user_id = ?", (uid,)).fetchall()]
    focus = [dict(r) for r in conn.execute("SELECT duration_minutes, completed_at FROM focus_sessions WHERE user_id = ? AND mode = 'focus'", (uid,)).fetchall()]
    conn.close()

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t["completed"] == 1)
    avg_stress = round(sum(c["stress_level"] for c in checkins) / len(checkins), 1) if checkins else 0
    avg_energy = round(sum(c["energy_level"] for c in checkins) / len(checkins), 1) if checkins else 0

    return {
        "summary": {
            "totalCheckins": len(checkins),
            "avgStress": avg_stress,
            "avgEnergy": avg_energy,
            "totalTasks": total_tasks,
            "completedTasks": completed_tasks,
            "completionRate": round((completed_tasks / total_tasks) * 100) if total_tasks else 0,
            "totalFocusSessions": len(focus),
            "totalFocusMinutes": sum(f["duration_minutes"] for f in focus),
        },
        "weeklyTrends": [
            {
                "date": c["created_at"][:10],
                "moodScore": MOOD_SCORES.get(c["mood"], 3),
                "stress": c["stress_level"],
                "energy": c["energy_level"],
                "mood": c["mood"],
            }
            for c in checkins[-10:]
        ],
        "moodCounts": [{"mood": m, "count": sum(1 for c in checkins if c["mood"] == m)} for m in sorted(ALLOWED_MOODS)],
        "focusByDay": [],
        "insights": ["Log mood check-ins and focus sessions consistently to track wellbeing patterns."],
    }


@app.get("/api/privacy")
def get_privacy(payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    prefs = dict(conn.execute("SELECT privacy_anonymous_community, privacy_include_insights, privacy_retention_days FROM users WHERE id = ?", (uid,)).fetchone())
    counts = {
        "moodCheckins": conn.execute("SELECT COUNT(*) FROM mood_checkins WHERE user_id = ?", (uid,)).fetchone()[0],
        "studyTasks": conn.execute("SELECT COUNT(*) FROM study_tasks WHERE user_id = ?", (uid,)).fetchone()[0],
        "chatMessages": conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (uid,)).fetchone()[0],
        "focusSessions": conn.execute("SELECT COUNT(*) FROM focus_sessions WHERE user_id = ?", (uid,)).fetchone()[0],
    }
    conn.close()
    return {"preferences": prefs, "counts": counts}


@app.put("/api/privacy")
def update_privacy(data: PrivacyInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET privacy_anonymous_community = ?, privacy_include_insights = ?, privacy_retention_days = ? WHERE id = ?",
        (1 if data.privacy_anonymous_community else 0, 1 if data.privacy_include_insights else 0, data.privacy_retention_days, payload["userId"]),
    )
    conn.commit()
    conn.close()
    return {"preferences": data.model_dump()}


@app.get("/api/privacy/export")
def export_privacy(payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    user = safe_user(conn, uid)
    moods = [dict(r) for r in conn.execute("SELECT mood, stress_level, energy_level, note, created_at FROM mood_checkins WHERE user_id = ?", (uid,)).fetchall()]
    tasks = [dict(r) for r in conn.execute("SELECT subject, title, description, deadline, priority, scheduled_slot, completed FROM study_tasks WHERE user_id = ?", (uid,)).fetchall()]
    focus = [dict(r) for r in conn.execute("SELECT mode, duration_minutes, subject, completed_at FROM focus_sessions WHERE user_id = ?", (uid,)).fetchall()]
    conn.close()
    return {"exportedAt": datetime.now(timezone.utc).isoformat(), "profile": user, "moodCheckins": moods, "studyTasks": tasks, "focusSessions": focus}


@app.delete("/api/privacy/data")
def delete_privacy_data(scope: str, payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    if scope == "moods":
        conn.execute("DELETE FROM mood_checkins WHERE user_id = ?", (uid,))
    elif scope == "chat":
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (uid,))
    elif scope == "all":
        conn.execute("DELETE FROM mood_checkins WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM focus_sessions WHERE user_id = ?", (uid,))
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid scope.")
    conn.commit()
    conn.close()
    return {"deleted": True, "scope": scope}


@app.get("/api/community/posts")
def get_community_posts(payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    posts = conn.execute(
        """
        SELECT p.id, p.user_id, p.author_alias, p.category, p.title, p.content, p.reported, p.created_at,
               (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.reaction_type = 'heart') AS heart_count,
               (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.reaction_type = 'helpful') AS helpful_count,
               (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.user_id = ? AND r.reaction_type = 'heart') AS user_hearted,
               (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.user_id = ? AND r.reaction_type = 'helpful') AS user_helpful
        FROM community_posts p ORDER BY datetime(p.created_at) DESC, p.id DESC
        """,
        (uid, uid),
    ).fetchall()
    comments = conn.execute("SELECT id, post_id, author_alias, content, reported, created_at FROM community_comments ORDER BY id ASC").fetchall()
    by_post = {}
    for c in comments:
        by_post.setdefault(c["post_id"], []).append(dict(c))
    result = []
    for p in posts:
        d = dict(p)
        d["is_owner"] = d.pop("user_id") == uid
        d["reported"] = bool(d["reported"])
        d["user_hearted"] = bool(d["user_hearted"])
        d["user_helpful"] = bool(d["user_helpful"])
        d["comments"] = by_post.get(d["id"], [])
        result.append(d)
    conn.close()
    return {"posts": result}


@app.post("/api/community/posts", status_code=201)
def create_community_post(data: PostInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    u = conn.execute("SELECT name, community_alias, privacy_anonymous_community FROM users WHERE id = ?", (uid,)).fetchone()
    alias = u["community_alias"] if u["privacy_anonymous_community"] else u["name"].split()[0]
    cur = conn.execute(
        "INSERT INTO community_posts (user_id, author_alias, category, title, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (uid, alias, data.category, data.title.strip(), data.content.strip(), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return {"id": cur.lastrowid}


@app.post("/api/community/posts/{post_id}/react")
def react_community_post(post_id: int, data: ReactInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    existing = conn.execute(
        "SELECT id FROM community_reactions WHERE post_id = ? AND user_id = ? AND reaction_type = ?",
        (post_id, uid, data.reaction_type),
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM community_reactions WHERE id = ?", (existing["id"],))
        active = False
    else:
        conn.execute("INSERT INTO community_reactions (post_id, user_id, reaction_type) VALUES (?, ?, ?)", (post_id, uid, data.reaction_type))
        active = True
    conn.commit()
    conn.close()
    return {"active": active}


@app.post("/api/community/posts/{post_id}/comments", status_code=201)
def comment_community_post(post_id: int, data: CommentInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    uid = payload["userId"]
    u = conn.execute("SELECT name, community_alias, privacy_anonymous_community FROM users WHERE id = ?", (uid,)).fetchone()
    alias = u["community_alias"] if u["privacy_anonymous_community"] else u["name"].split()[0]
    conn.execute(
        "INSERT INTO community_comments (post_id, user_id, author_alias, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (post_id, uid, alias, data.content.strip(), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return {"added": True}


@app.post("/api/community/posts/{post_id}/report")
def report_community_post(post_id: int, data: ReportInput, payload: dict = Depends(verify_token)):
    conn = get_connection()
    conn.execute("UPDATE community_posts SET reported = 1, report_reason = ? WHERE id = ?", (data.reason, post_id))
    conn.commit()
    conn.close()
    return {"reported": True}


@app.delete("/api/community/posts/{post_id}")
def delete_community_post(post_id: int, payload: dict = Depends(verify_token)):
    conn = get_connection()
    cur = conn.execute("DELETE FROM community_posts WHERE id = ? AND user_id = ?", (post_id, payload["userId"]))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=403, detail="Not permitted.")
    return {"deleted": True}


@app.get("/api/support/counsellors")
def get_counsellors(payload: dict = Depends(verify_token)):
    conn = get_connection()
    reqs = [dict(r) for r in conn.execute("SELECT id, counsellor_name, preferred_slot, topic, status, created_at FROM counsellor_requests WHERE user_id = ? ORDER BY id DESC", (payload["userId"],)).fetchall()]
    conn.close()
    return {
        "counsellors": [
            {
                "id": "c1",
                "name": "Dr. Ananya Rao",
                "role": "Lead Campus Wellbeing Counsellor",
                "focus": "Academic Stress · Exam Anxiety · Adjustment",
                "office": "Student Wellness Wing, Room 204",
                "hours": "Mon – Fri, 09:00 AM – 05:00 PM",
                "contactEmail": "wellness-office@campus.example.edu",
                "phone": "+1 (555) 234-8910",
            },
            {
                "id": "c2",
                "name": "Marcus Bennett, LCSW",
                "role": "Graduate & Postgraduate Support Specialist",
                "focus": "Burnout Recovery · Thesis Pressure · Work-Life Balance",
                "office": "Student Wellness Wing, Room 208",
                "hours": "Tue – Sat, 10:00 AM – 06:00 PM",
                "contactEmail": "grad-support@campus.example.edu",
                "phone": "+1 (555) 234-8914",
            },
        ],
        "requests": reqs,
    }


@app.post("/api/support/request", status_code=201)
def create_support_request(data: SupportRequestInput, payload: dict = Depends(verify_token)):
    if not data.consent_given:
        raise HTTPException(status_code=400, detail="Explicit consent is required.")
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO counsellor_requests (user_id, counsellor_name, preferred_slot, topic, consent_given, status) VALUES (?, ?, ?, ?, 1, 'Consent Recorded · Ready for Confirmation')",
        (payload["userId"], data.counsellor_name, data.preferred_slot, data.topic),
    )
    row = dict(conn.execute("SELECT id, counsellor_name, preferred_slot, topic, status, created_at FROM counsellor_requests WHERE id = ?", (cur.lastrowid,)).fetchone())
    conn.commit()
    conn.close()
    return {"request": row}

