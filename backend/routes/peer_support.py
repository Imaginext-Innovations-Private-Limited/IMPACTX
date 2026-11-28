
from flask import Blueprint, request, jsonify, session
from database import get_db_connection

peer_support = Blueprint("peer_support", __name__)


# 1. Get all peer support posts
@peer_support.route("/", methods=["GET"])
def get_posts():

    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    student_id = session["student_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.post_id,
            p.student_id,
            s.full_name,
            p.title,
            p.content,
            p.created_at,
            (SELECT COUNT(*)
             FROM peer_likes l
             WHERE l.post_id = p.post_id) AS likes_count,
            (SELECT COUNT(*)
             FROM peer_replies r
             WHERE r.post_id = p.post_id) AS replies_count,
            EXISTS (
                SELECT 1
                FROM peer_likes l
                WHERE l.post_id = p.post_id
                AND l.student_id = %s
            ) AS liked_by_me
        FROM peer_posts p
        JOIN students s ON p.student_id = s.student_id
        ORDER BY p.created_at DESC
    """, (student_id,))

    posts = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(posts), 200


# 2. Create a new post
@peer_support.route("/", methods=["POST"])
def create_post():

    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    data = request.get_json() or {}

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return jsonify({
            "message": "Title and content are required"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO peer_posts
        (student_id, title, content)
        VALUES (%s, %s, %s)
    """, (session["student_id"], title, content))

    conn.commit()

    post_id = cursor.lastrowid

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Post created successfully",
        "post_id": post_id
    }), 201


# 3. Get replies for a post
@peer_support.route("/<int:post_id>/replies", methods=["GET"])
def get_replies(post_id):

    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            r.reply_id,
            r.post_id,
            r.student_id,
            s.full_name,
            r.reply_content,
            r.created_at
        FROM peer_replies r
        JOIN students s ON r.student_id = s.student_id
        WHERE r.post_id = %s
        ORDER BY r.created_at ASC
    """, (post_id,))

    replies = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(replies), 200


# 4. Add a reply
@peer_support.route("/<int:post_id>/replies", methods=["POST"])
def add_reply(post_id):

    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    data = request.get_json() or {}
    reply_content = data.get("reply_content", "").strip()

    if not reply_content:
        return jsonify({
            "message": "Reply cannot be empty"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT post_id FROM peer_posts
        WHERE post_id = %s
    """, (post_id,))

    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"message": "Post not found"}), 404

    cursor.execute("""
        INSERT INTO peer_replies
        (post_id, student_id, reply_content)
        VALUES (%s, %s, %s)
    """, (post_id, session["student_id"], reply_content))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Reply added successfully"
    }), 201


# 5. Like or unlike a post
@peer_support.route("/<int:post_id>/like", methods=["POST"])
def toggle_like(post_id):

    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    student_id = session["student_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT post_id FROM peer_posts
        WHERE post_id = %s
    """, (post_id,))

    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"message": "Post not found"}), 404

    cursor.execute("""
        SELECT like_id FROM peer_likes
        WHERE post_id = %s AND student_id = %s
    """, (post_id, student_id))

    existing_like = cursor.fetchone()

    if existing_like:
        cursor.execute("""
            DELETE FROM peer_likes
            WHERE post_id = %s AND student_id = %s
        """, (post_id, student_id))
        message = "Like removed"
        liked = False
    else:
        cursor.execute("""
            INSERT INTO peer_likes (post_id, student_id)
            VALUES (%s, %s)
        """, (post_id, student_id))
        message = "Post liked"
        liked = True

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": message,
        "liked": liked
    }), 200


# 6. Delete your own post
@peer_support.route("/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):

    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM peer_posts
        WHERE post_id = %s AND student_id = %s
    """, (post_id, session["student_id"]))

    conn.commit()

    deleted = cursor.rowcount

    cursor.close()
    conn.close()

    if deleted == 0:
        return jsonify({
            "message": "Post not found or you cannot delete this post"
        }), 404

    return jsonify({
        "message": "Post deleted successfully"
    }), 200
