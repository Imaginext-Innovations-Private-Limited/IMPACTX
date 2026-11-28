
import { useEffect, useState } from "react";
import axios from "axios";
import {
  Heart,
  MessageCircle,
  Send,
  Plus,
  Trash2,
  Users,
  RefreshCw
} from "lucide-react";
import "./PeerSupport.css";

const API = "http://localhost:5000/api/peer/";

function PeerSupport() {
  const [posts, setPosts] = useState([]);
  const [currentStudentId, setCurrentStudentId] = useState(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [replyInputs, setReplyInputs] = useState({});
  const [replies, setReplies] = useState({});
  const [expandedPost, setExpandedPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Load all posts
  const fetchPosts = async () => {
    try {
      setError("");

      const response = await axios.get(API, {
        withCredentials: true
      });

      setPosts(response.data);
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to load discussions. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  fetchPosts();
  fetchCurrentStudent();
}, []);

const fetchCurrentStudent = async () => {
  try {
    const response = await axios.get(
      "http://localhost:5000/api/auth/me",
      { withCredentials: true }
    );

    setCurrentStudentId(
      Number(response.data.student.student_id)
    );
  } catch (err) {
    console.error("Unable to fetch current student:", err);
  }
};

  // Create post
  const handleCreatePost = async (e) => {
    e.preventDefault();

    if (!title.trim() || !content.trim()) {
      setError("Please enter both title and description.");
      return;
    }

    try {
      setPosting(true);
      setError("");
      setMessage("");

      await axios.post(
        API,
        {
          title: title.trim(),
          content: content.trim()
        },
        { withCredentials: true }
      );

      setTitle("");
      setContent("");
      setMessage("Your discussion was shared successfully!");

      await fetchPosts();
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to create your post."
      );
    } finally {
      setPosting(false);
    }
  };

  // Load replies
  const fetchReplies = async (postId) => {
    try {
      const response = await axios.get(
        `${API}${postId}/replies`,
        { withCredentials: true }
      );

      setReplies((prev) => ({
        ...prev,
        [postId]: response.data
      }));
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to load replies."
      );
    }
  };

  // Open or close reply section
  const toggleReplies = async (postId) => {
    if (expandedPost === postId) {
      setExpandedPost(null);
      return;
    }

    setExpandedPost(postId);
    await fetchReplies(postId);
  };

  // Add reply
  const handleReply = async (postId) => {
    const replyContent = replyInputs[postId]?.trim();

    if (!replyContent) return;

    try {
      await axios.post(
        `${API}${postId}/replies`,
        { reply_content: replyContent },
        { withCredentials: true }
      );

      setReplyInputs((prev) => ({
        ...prev,
        [postId]: ""
      }));

      await fetchReplies(postId);
      await fetchPosts();
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to add reply."
      );
    }
  };

  // Like or unlike
  const handleLike = async (postId) => {
    try {
      await axios.post(
        `${API}${postId}/like`,
        {},
        { withCredentials: true }
      );

      await fetchPosts();
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to update like."
      );
    }
  };

  // Delete own post
  const handleDelete = async (postId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this discussion?"
    );

    if (!confirmed) return;

    try {
      await axios.delete(
        `${API}${postId}`,
        { withCredentials: true }
      );

      setMessage("Discussion deleted successfully.");
      setExpandedPost(null);
      await fetchPosts();
    } catch (err) {
      setError(
        err.response?.data?.message ||
        "Unable to delete this post."
      );
    }
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleString();
  };

  return (
    <div className="peer-page">

      <div className="peer-header">
        <div>
          <span className="peer-eyebrow">
            STUDENT COMMUNITY
          </span>
          <h1>Peer Support</h1>
          <p>
            A safe space to connect, share and support
            one another.
          </p>
        </div>

        <div className="peer-header-icon">
          <Users size={32} />
        </div>
      </div>

      <div className="peer-welcome">
        <div>
          <h3>You are not alone 💜</h3>
          <p>
            Everyone has challenges. Share your experiences,
            encourage others and grow together.
          </p>
        </div>
      </div>

      {/* Create discussion */}
      <div className="peer-create-card">
        <h2>
          <Plus size={21} />
          Start a discussion
        </h2>

        <form onSubmit={handleCreatePost}>
          <input
            type="text"
            placeholder="Give your discussion a title..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
          />

          <textarea
            placeholder="What's on your mind? Share your thoughts..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
          />

          <button
            type="submit"
            className="peer-post-btn"
            disabled={posting}
          >
            <Send size={17} />
            {posting ? "Sharing..." : "Share discussion"}
          </button>
        </form>
      </div>

      {error && (
        <div className="peer-alert peer-error">
          {error}
        </div>
      )}

      {message && (
        <div className="peer-alert peer-success">
          {message}
        </div>
      )}

      {/* Discussion feed */}
      <div className="peer-feed-heading">
        <div>
          <h2>Community discussions</h2>
          <p>Connect with fellow students</p>
        </div>

        <button
          className="peer-refresh-btn"
          onClick={fetchPosts}
          title="Refresh discussions"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {loading ? (
        <div className="peer-empty">
          Loading discussions...
        </div>
      ) : posts.length === 0 ? (
        <div className="peer-empty">
          <Users size={35} />
          <h3>No discussions yet</h3>
          <p>
            Be the first to share something with your community.
          </p>
        </div>
      ) : (
        <div className="peer-post-list">
          {posts.map((post) => (
            <div className="peer-post-card" key={post.post_id}>

              <div className="peer-post-top">
                <div className="peer-avatar">
                  {post.full_name?.charAt(0).toUpperCase()}
                </div>

                <div className="peer-author">
                  <strong>{post.full_name}</strong>
                  <span>{formatDate(post.created_at)}</span>
                </div>

                <div className="peer-delete">
  {currentStudentId !== null &&
    Number(post.student_id) === currentStudentId && (
      <button
        onClick={() => handleDelete(post.post_id)}
        title="Delete your post"
      >
        <Trash2 size={17} />
      </button>
    )}
</div>
              </div>

              <div className="peer-post-body">
                <h3>{post.title}</h3>
                <p>{post.content}</p>
              </div>

              <div className="peer-post-actions">
                <button
                  className={post.liked_by_me ? "liked" : ""}
                  onClick={() => handleLike(post.post_id)}
                >
                  <Heart
                    size={18}
                    fill={post.liked_by_me ? "currentColor" : "none"}
                  />
                  {post.likes_count} Likes
                </button>

                <button
                  onClick={() => toggleReplies(post.post_id)}
                >
                  <MessageCircle size={18} />
                  {post.replies_count} Replies
                </button>
              </div>

              {expandedPost === post.post_id && (
                <div className="peer-reply-section">

                  <h4>Replies</h4>

                  {replies[post.post_id]?.length > 0 ? (
                    replies[post.post_id].map((reply) => (
                      <div
                        className="peer-reply"
                        key={reply.reply_id}
                      >
                        <strong>{reply.full_name}</strong>
                        <p>{reply.reply_content}</p>
                        <span>{formatDate(reply.created_at)}</span>
                      </div>
                    ))
                  ) : (
                    <p className="peer-no-replies">
                      No replies yet. Be the first to respond!
                    </p>
                  )}

                  <div className="peer-reply-input">
                    <input
                      type="text"
                      placeholder="Write a supportive reply..."
                      value={replyInputs[post.post_id] || ""}
                      onChange={(e) =>
                        setReplyInputs((prev) => ({
                          ...prev,
                          [post.post_id]: e.target.value
                        }))
                      }
                    />

                    <button
                      onClick={() => handleReply(post.post_id)}
                    >
                      <Send size={17} />
                    </button>
                  </div>

                </div>
              )}

            </div>
          ))}
        </div>
      )}

      <div className="peer-guidelines">
        <h3>Community guidelines 💜</h3>
        <ul>
          <li>Be kind and respectful to everyone.</li>
          <li>Respect other students' privacy.</li>
          <li>Offer encouragement, not judgment.</li>
          <li>Do not share sensitive personal information.</li>
          <li>Peer support is not a replacement for professional help.</li>
        </ul>
      </div>

    </div>
  );
}

export default PeerSupport;
