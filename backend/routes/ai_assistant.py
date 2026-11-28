
import requests
from flask import Blueprint, jsonify, request, session
from database import get_db_connection

ai_assistant = Blueprint("ai_assistant", __name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2:latest"

SYSTEM_PROMPT = """
You are a supportive AI Wellbeing Assistant for a student wellbeing
application.

Your purpose is to support students with:
- Academic stress and examination pressure
- Emotional challenges and everyday worries
- Study planning and time management
- Motivation and personal development
- Maintaining a healthy study-life balance

Communication guidelines:
1. Listen carefully and understand the student's message.
2. Respond naturally, warmly, respectfully and empathetically.
3. Give relevant and practical suggestions.
4. Ask appropriate follow-up questions when useful.
5. Remember the context of the current conversation.
6. Avoid repeating generic responses.
7. Use simple, clear language.
8. Do not diagnose medical or mental health conditions.
9. Do not claim to be a doctor, therapist or counsellor.
10. Encourage professional support when a student needs it.

Safety:
- If a student expresses suicidal thoughts, self-harm intentions,
  or immediate danger, take the concern seriously.
- Encourage the student to contact emergency services or a trusted
  person immediately.
- For students in India, emergency assistance can be reached at 112.
- Never dismiss, shame or judge a student's feelings.

You are an AI support tool, not a replacement for professional care.
"""


def generate_response(student_id, message):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Retrieve recent conversations belonging to this student.
        cursor.execute("""
            SELECT user_message, ai_response
            FROM ai_chat_history
            WHERE student_id = %s
            ORDER BY created_at DESC, chat_id DESC
            LIMIT 10
        """, (student_id,))

        previous_chats = cursor.fetchall()

        # Reverse records to maintain chronological order.
        previous_chats = list(reversed(previous_chats))

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        # Add previous conversations as context.
        for user_message, ai_response in previous_chats:
            messages.append({
                "role": "user",
                "content": user_message
            })

            messages.append({
                "role": "assistant",
                "content": ai_response
            })

        # Add the latest student message.
        messages.append({
            "role": "user",
            "content": message
        })

        # Send the conversation to the local Ollama model.
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        ai_response = result.get(
            "message", {}
        ).get("content", "").strip()

        if not ai_response:
            raise ValueError("The LLM returned an empty response.")

        return ai_response

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@ai_assistant.route("/chat", methods=["POST"])
def chat():

    if "student_id" not in session:
        return jsonify({
            "message": "Please log in first."
        }), 401

    data = request.get_json() or {}

    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "message": "Please enter a message."
        }), 400

    if len(message) > 4000:
        return jsonify({
            "message": "Please keep your message under 4000 characters."
        }), 400

    connection = None
    cursor = None

    try:
        student_id = session["student_id"]

        # Generate a response using Llama 3.2.
        ai_response = generate_response(
            student_id,
            message
        )

        # Save the conversation in MySQL.
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO ai_chat_history
            (student_id, user_message, ai_response)
            VALUES (%s, %s, %s)
        """, (
            student_id,
            message,
            ai_response
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "user_message": message,
            "ai_response": ai_response
        })

    except requests.exceptions.ConnectionError:
        return jsonify({
            "message": (
                "Unable to connect to Ollama. "
                "Please make sure Ollama is running."
            )
        }), 503

    except requests.exceptions.Timeout:
        return jsonify({
            "message": (
                "The AI is taking longer than expected. "
                "Please try again."
            )
        }), 504

    except requests.exceptions.RequestException:
        return jsonify({
            "message": "Unable to generate an AI response. Please try again."
        }), 502

    except Exception:
        if connection:
            connection.rollback()

        app_error = "An error occurred while processing your message."

        return jsonify({
            "message": app_error
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@ai_assistant.route("/history", methods=["GET"])
def history():

    if "student_id" not in session:
        return jsonify({
            "message": "Please log in first."
        }), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT chat_id, user_message, ai_response, created_at
            FROM ai_chat_history
            WHERE student_id = %s
            ORDER BY created_at ASC, chat_id ASC
        """, (session["student_id"],))

        chats = cursor.fetchall()

        for chat_item in chats:
            chat_item["created_at"] = (
                chat_item["created_at"].isoformat()
            )

        return jsonify({
            "status": "success",
            "history": chats
        })

    except Exception:
        return jsonify({
            "message": "Unable to retrieve chat history."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
