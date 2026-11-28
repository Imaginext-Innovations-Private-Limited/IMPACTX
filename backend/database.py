import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "tutor.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            student_id TEXT,
            student_name TEXT,
            concept TEXT,
            mastery_score INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            last_updated TIMESTAMP,
            PRIMARY KEY (student_id, concept)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            concept TEXT,
            role TEXT,
            message TEXT,
            timestamp TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def record_interaction(student_id: str, concept: str, role: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interactions (student_id, concept, role, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (student_id, concept, role, str(message), datetime.now()))
    conn.commit()
    conn.close()

def update_mastery(student_id: str, student_name: str, concept: str, score_delta: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO students (student_id, name) VALUES (?, ?)
    """, (student_id, student_name))
    
    cursor.execute("""
        SELECT mastery_score, attempts FROM progress 
        WHERE student_id = ? AND concept = ?
    """, (student_id, concept))
    row = cursor.fetchone()
    
    if row:
        current_score = row["mastery_score"]
        current_attempts = row["attempts"]
        new_score = max(0, min(100, current_score + score_delta))
        new_attempts = current_attempts + 1
        cursor.execute("""
            UPDATE progress 
            SET mastery_score = ?, attempts = ?, student_name = ?, last_updated = ?
            WHERE student_id = ? AND concept = ?
        """, (new_score, new_attempts, student_name, datetime.now(), student_id, concept))
    else:
        new_score = max(0, min(100, max(10, score_delta)))
        cursor.execute("""
            INSERT INTO progress (student_id, student_name, concept, mastery_score, attempts, last_updated)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (student_id, student_name, concept, new_score, datetime.now()))
    
    conn.commit()
    conn.close()
    return new_score

def get_student_score(student_id: str, concept: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mastery_score FROM progress WHERE student_id = ? AND concept = ?
    """, (student_id, concept))
    row = cursor.fetchone()
    conn.close()
    return row["mastery_score"] if row else 0

def get_teacher_analytics_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT student_name, concept, mastery_score, attempts, last_updated FROM progress")
    rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT concept, AVG(mastery_score) as avg_mastery, COUNT(DISTINCT student_id) as student_count FROM progress GROUP BY concept")
    concept_summary = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT student_name, AVG(mastery_score) as student_avg, SUM(attempts) as total_attempts FROM progress GROUP BY student_name")
    student_summary = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "records": rows,
        "concept_summary": concept_summary,
        "student_summary": student_summary
    }
