import sqlite3
from backend.database import DB_PATH

DIFFICULTY_MAP = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}

def update_concept_mastery(student_id: str, concept: str, is_correct: bool, hints_used: int) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM concept_mastery WHERE student_id = ? AND concept = ?", (student_id, concept))
        row = cursor.fetchone()

        score = row["mastery_score"] if row else 0.0
        diff = row["current_difficulty"] if row else 1

        # Reward correct answers based on independence; penalize slight over-reliance on hints
        delta = 20.0 if is_correct else -10.0
        delta -= (hints_used * 4.0)

        new_score = max(0.0, min(100.0, score + delta))

        # Dynamically adjust difficulty level
        if new_score >= 70.0 and diff < 3:
            diff += 1
        elif new_score < 35.0 and diff > 1:
            diff -= 1

        cursor.execute("""
            INSERT INTO concept_mastery (student_id, concept, mastery_score, current_difficulty, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id, concept) DO UPDATE SET
                mastery_score = excluded.mastery_score,
                current_difficulty = excluded.current_difficulty,
                last_updated = CURRENT_TIMESTAMP
        """, (student_id, concept, new_score, diff))
        conn.commit()

        return {
            "concept": concept,
            "mastery_score": round(new_score, 1),
            "difficulty_level": diff,
            "difficulty_label": DIFFICULTY_MAP[diff]
        }
