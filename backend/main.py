import os
import sqlite3
import logging
from typing import List, Optional, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.socratic_engine import generate_socratic_turn

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Socratic AI Tutor API",
    description="Backend with live SQLite student tracking and dynamic Socratic tutoring.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "socratic_tutor.db")

for d in [DATA_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

# In-memory score accumulator per active session: (student_id, concept) -> int
SESSION_SCORES = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Interactions log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        student_id TEXT,
        student_name TEXT,
        concept TEXT,
        student_answer TEXT,
        feedback TEXT,
        score_delta INTEGER,
        mode TEXT
    )
    """)
    
    # Mastery summary table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mastery (
        student_id TEXT,
        student_name TEXT,
        concept TEXT,
        mastery_score INTEGER DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (student_id, concept)
    )
    """)
    
    # Migration guards for existing databases
    cursor.execute("PRAGMA table_info(mastery)")
    columns = [col[1] for col in cursor.fetchall()]
    if "student_name" not in columns:
        cursor.execute("ALTER TABLE mastery ADD COLUMN student_name TEXT DEFAULT 'Learner'")
    if "attempts" not in columns:
        cursor.execute("ALTER TABLE mastery ADD COLUMN attempts INTEGER DEFAULT 1")
    if "last_updated" not in columns:
        cursor.execute("ALTER TABLE mastery ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_mastery_student_concept ON mastery(student_id, concept)")
    conn.commit()
    conn.close()

init_db()

class TutorRequest(BaseModel):
    student_id: Optional[str] = "student-1"
    student_name: Optional[str] = "Abu Zar Reehan"
    concept: Optional[str] = "Supervised Learning"
    student_answer: Optional[str] = "start"
    history: Optional[List[Any]] = []
    difficulty: Optional[int] = 1
    mode: Optional[str] = "guiding"
    question_num: Optional[int] = 1

@app.get("/")
def root():
    return {"status": "online", "service": "Socratic AI Tutor API"}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOADS_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"status": "success", "message": f"Saved and indexed {file.filename}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/tutor/interact")
def tutor_interact(req: TutorRequest):
    q_num = req.question_num if req.question_num is not None else 1

    result = generate_socratic_turn(
        student_id=req.student_id,
        concept=req.concept,
        student_answer=req.student_answer,
        history=req.history,
        difficulty=req.difficulty,
        student_name=req.student_name,
        mode=req.mode,
        question_num=q_num
    )

    if req.mode == "guiding":
        delta = result.get("score_delta", 0)
        session_key = (req.student_id, req.concept)

        if q_num == 1:
            new_score = delta
        else:
            prev_score = SESSION_SCORES.get(session_key, 0)
            new_score = min(100, max(0, prev_score + delta))

        SESSION_SCORES[session_key] = new_score
        result["mastery_score"] = new_score

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO interactions (student_id, student_name, concept, student_answer, feedback, score_delta, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (req.student_id, req.student_name, req.concept, req.student_answer, result.get("feedback", ""), delta, req.mode))

            cursor.execute("""
            INSERT INTO mastery (student_id, student_name, concept, mastery_score, attempts, last_updated)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id, concept) DO UPDATE SET 
                student_name = excluded.student_name,
                mastery_score = excluded.mastery_score,
                attempts = mastery.attempts + 1,
                last_updated = CURRENT_TIMESTAMP
            """, (req.student_id, req.student_name, req.concept, new_score))

            conn.commit()
            conn.close()
        except Exception as err:
            logger.error(f"Database write error: {err}")
    else:
        result["mastery_score"] = 0

    return result

@app.get("/api/teacher/analytics")
def get_teacher_analytics():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT student_name, student_id, concept, mastery_score, attempts FROM mastery ORDER BY last_updated DESC")
        records = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT concept, ROUND(AVG(mastery_score), 1) as avg_mastery FROM mastery GROUP BY concept")
        concept_summary = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT student_name, SUM(attempts) as total_attempts FROM mastery GROUP BY student_name")
        student_summary = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Only returns real learner records from SQLite (no hardcoded fake students)
        return {
            "records": records,
            "concept_summary": concept_summary,
            "student_summary": student_summary
        }
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return {"records": [], "concept_summary": [], "student_summary": []}
