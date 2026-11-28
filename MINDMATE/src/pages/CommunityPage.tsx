import React, { useEffect, useState } from 'react';
import {
  Flag,
  Heart,
  MessageSquare,
  Plus,
  Send,
  ShieldAlert,
  ThumbsUp,
  Trash2,
} from 'lucide-react';
import type { CommunityPost } from '../types';
import { apiFetch } from '../api';

const CATEGORIES = ['All', 'Academic Stress', 'Small Wins', 'Study Tips', 'Self-Care', 'Encouragement'] as const;

export function CommunityPage() {
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [loading, setLoading] = useState(true);

  const [newCategory, setNewCategory] = useState('Academic Stress');
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [expandedPostId, setExpandedPostId] = useState<number | null>(null);
  const [commentInputs, setCommentInputs] = useState<Record<number, string>>({});
  const [reportingPostId, setReportingPostId] = useState<number | null>(null);
  const [reportReason, setReportReason] = useState('Contains distressing or inappropriate content');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  const loadPosts = async () => {
    try {
      const res = await apiFetch<{ posts: CommunityPost[] }>('/api/community/posts');
      setPosts(res.posts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load community posts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPosts();
  }, []);

  const handleCreatePost = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setFeedback('');
    try {
      await apiFetch('/api/community/posts', {
        method: 'POST',
        body: JSON.stringify({
          category: newCategory,
          title: newTitle,
          content: newContent,
        }),
      });
      setNewTitle('');
      setNewContent('');
      setFeedback('Your post was shared anonymously with the peer community.');
      await loadPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to publish post.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReact = async (postId: number, reactionType: 'heart' | 'helpful') => {
    try {
      await apiFetch(`/api/community/posts/${postId}/react`, {
        method: 'POST',
        body: JSON.stringify({ reaction_type: reactionType }),
      });
      await loadPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update reaction.');
    }
  };

  const handleAddComment = async (postId: number) => {
    const text = (commentInputs[postId] || '').trim();
    if (!text) return;
    try {
      await apiFetch(`/api/community/posts/${postId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: text }),
      });
      setCommentInputs((prev) => ({ ...prev, [postId]: '' }));
      await loadPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to post reply.');
    }
  };

  const handleReportSubmit = async (postId: number) => {
    try {
      await apiFetch(`/api/community/posts/${postId}/report`, {
        method: 'POST',
        body: JSON.stringify({ reason: reportReason }),
      });
      setReportingPostId(null);
      setFeedback('Post flagged for community moderation review.');
      await loadPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to submit report.');
    }
  };

  const handleDeletePost = async (postId: number) => {
    try {
      await apiFetch(`/api/community/posts/${postId}`, { method: 'DELETE' });
      setPosts((prev) => prev.filter((p) => p.id !== postId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete post.');
    }
  };

  const visiblePosts =
    selectedCategory === 'All'
      ? posts
      : posts.filter((p) => p.category === selectedCategory);

  return (
    <div className="space-y-6">
      <div className="bg-[#ECFDF5]/70 border border-teal-200/80 rounded-2xl px-5 py-3.5 text-xs sm:text-sm text-teal-950">
        Peer Support Community uses anonymous campus aliases by default. Personal emails, majors, and private mood records are never shown publicly.
      </div>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Create Post Form */}
        <form
          onSubmit={handleCreatePost}
          className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4 h-fit"
        >
          <h2 className="font-display text-lg font-semibold text-slate-900">Share with Peers</h2>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="post-category">
              Topic Category
            </label>
            <select
              id="post-category"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            >
              {CATEGORIES.filter((c) => c !== 'All').map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="post-title">
              Title
            </label>
            <input
              id="post-title"
              type="text"
              required
              minLength={3}
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g., Small habit that helped me today"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="post-content">
              Experience or Tip
            </label>
            <textarea
              id="post-content"
              rows={4}
              required
              minLength={8}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Share encouragement or study lessons kindly. Avoid personal contact details."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>

          {error && <p className="text-xs text-rose-700">{error}</p>}
          {feedback && <p className="text-xs text-teal-700">{feedback}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors inline-flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <Plus className="w-4 h-4" />
            <span>{submitting ? 'Posting...' : 'Publish Anonymously'}</span>
          </button>
        </form>

        {/* Community Feed */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex flex-wrap items-center gap-1.5 p-1.5 bg-white rounded-xl border border-slate-200/80">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                  selectedCategory === cat
                    ? 'bg-[#EDE9FE] text-[#4338CA]'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {loading ? (
            <p className="text-sm text-slate-500">Loading peer stories...</p>
          ) : visiblePosts.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-8 text-center text-sm text-slate-500">
              No posts in this category yet. Start the conversation on the left!
            </div>
          ) : (
            <div className="space-y-4">
              {visiblePosts.map((post) => {
                const isExpanded = expandedPostId === post.id;
                return (
                  <article
                    key={post.id}
                    className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                          <span className="font-semibold text-slate-800">{post.author_alias}</span>
                          <span aria-hidden="true">·</span>
                          <span className="text-[#5B4FE9] font-medium">{post.category}</span>
                          <span aria-hidden="true">·</span>
                          <span>{new Date(post.created_at).toLocaleDateString()}</span>
                        </div>
                        <h3 className="font-display text-lg font-semibold text-slate-900">{post.title}</h3>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {post.is_owner && (
                          <button
                            type="button"
                            onClick={() => handleDeletePost(post.id)}
                            className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                            aria-label="Delete your post"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setReportingPostId(reportingPostId === post.id ? null : post.id)}
                          className="p-2 rounded-lg text-slate-400 hover:text-amber-700 hover:bg-amber-50"
                          aria-label="Report post for moderation"
                        >
                          <Flag className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {post.reported && (
                      <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 shrink-0" />
                        <span>This post has been flagged for moderator review.</span>
                      </div>
                    )}

                    <p className="text-sm text-slate-700 leading-relaxed">{post.content}</p>

                    {reportingPostId === post.id && (
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                        <p className="text-xs font-semibold text-slate-900">Report Post for Moderation</p>
                        <select
                          value={reportReason}
                          onChange={(e) => setReportReason(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs bg-white"
                        >
                          <option value="Contains distressing or inappropriate content">
                            Distressing or inappropriate content
                          </option>
                          <option value="Contains personal identifying information">
                            Exposes personal information
                          </option>
                          <option value="Spam or disrespectful language">
                            Spam or disrespectful language
                          </option>
                        </select>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleReportSubmit(post.id)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800"
                          >
                            Submit Report
                          </button>
                          <button
                            type="button"
                            onClick={() => setReportingPostId(null)}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Actions Row */}
                    <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        onClick={() => handleReact(post.id, 'heart')}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          post.user_hearted
                            ? 'bg-rose-50 border-rose-200 text-rose-700'
                            : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <Heart className="w-3.5 h-3.5" />
                        <span className="font-mono-tabular">{post.heart_count}</span>
                        <span>Support</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleReact(post.id, 'helpful')}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          post.user_helpful
                            ? 'bg-[#ECFDF5] border-teal-200 text-teal-800'
                            : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span className="font-mono-tabular">{post.helpful_count}</span>
                        <span>Helpful</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setExpandedPostId(isExpanded ? null : post.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span className="font-mono-tabular">{post.comments.length}</span>
                        <span>{isExpanded ? 'Hide Replies' : 'Replies'}</span>
                      </button>
                    </div>

                    {/* Comments Thread */}
                    {isExpanded && (
                      <div className="pt-3 border-t border-slate-100 space-y-3">
                        {post.comments.length > 0 && (
                          <ul className="space-y-2.5">
                            {post.comments.map((comment) => (
                              <li key={comment.id} className="p-3 rounded-xl bg-slate-50 text-xs space-y-1">
                                <div className="flex items-center gap-2 text-slate-500">
                                  <span className="font-semibold text-slate-800">{comment.author_alias}</span>
                                  <span aria-hidden="true">·</span>
                                  <span>{new Date(comment.created_at).toLocaleDateString()}</span>
                                </div>
                                <p className="text-sm text-slate-700">{comment.content}</p>
                              </li>
                            ))}
                          </ul>
                        )}

                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={commentInputs[post.id] || ''}
                            onChange={(e) =>
                              setCommentInputs((prev) => ({ ...prev, [post.id]: e.target.value }))
                            }
                            placeholder="Write an encouraging reply..."
                            className="flex-1 px-3.5 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                          />
                          <button
                            type="button"
                            onClick={() => handleAddComment(post.id)}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4]"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Reply</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
