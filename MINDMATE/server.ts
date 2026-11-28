import 'dotenv/config';
import express from 'express';
import path from 'path';
import fs from 'fs';
import { createServer as createViteServer } from 'vite';
import { db, initDatabase } from './src/server/db.ts';
import {
  createSessionToken,
  hashPassword,
  requireAuth,
  verifyPassword,
  type AuthenticatedRequest,
} from './src/server/auth.ts';
import { generateWellbeingReply } from './src/server/ai.ts';

initDatabase();

const app = express();
app.use(express.json({ limit: '1mb' }));

const ALLOWED_MOODS = ['Happy', 'Calm', 'Neutral', 'Stressed', 'Sad', 'Anxious'] as const;
const ALLOWED_PRIORITIES = ['low', 'medium', 'high'] as const;
const ALLOWED_CATEGORIES = ['Academic Stress', 'Small Wins', 'Study Tips', 'Self-Care', 'Encouragement'] as const;

const MOOD_SCORES: Record<string, number> = {
  Happy: 5,
  Calm: 4,
  Neutral: 3,
  Stressed: 2,
  Anxious: 2,
  Sad: 1,
};

function sanitizeAlias(name: string): string {
  const adjectives = ['Calm', 'Quiet', 'Gentle', 'Steady', 'Kind', 'Warm'];
  const trees = ['Maple', 'Cedar', 'Fern', 'Pine', 'Willow', 'Birch'];
  const hash = Array.from(name).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const adj = adjectives[hash % adjectives.length];
  const tree = trees[(hash >> 2) % trees.length];
  const num = 100 + (hash % 899);
  return `${adj} ${tree} #${num}`;
}

function getSafeUser(userId: number) {
  return db
    .prepare(`
      SELECT id, name, email, university, major, year_of_study, community_alias,
             is_demo, privacy_anonymous_community, privacy_include_insights,
             privacy_retention_days, created_at
      FROM users WHERE id = ?
    `)
    .get(userId) as Record<string, unknown> | undefined;
}

// ---------- AUTH ROUTES ----------

app.post('/api/auth/register', (req, res) => {
  const { name, email, password, university, major, year_of_study } = req.body ?? {};
  if (
    typeof name !== 'string' ||
    name.trim().length < 2 ||
    typeof email !== 'string' ||
    !email.includes('@') ||
    typeof password !== 'string' ||
    password.length < 6
  ) {
    res.status(400).json({ error: 'Please provide a valid name, email address, and password (6+ characters).' });
    return;
  }

  const normalizedEmail = email.trim().toLowerCase();
  const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(normalizedEmail);
  if (existing) {
    res.status(409).json({ error: 'An account with this email already exists. Please sign in instead.' });
    return;
  }

  const alias = sanitizeAlias(name.trim() + normalizedEmail);
  const result = db
    .prepare(`
      INSERT INTO users (name, email, password_hash, university, major, year_of_study, community_alias, is_demo)
      VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    `)
    .run(
      name.trim().slice(0, 80),
      normalizedEmail.slice(0, 120),
      hashPassword(password),
      typeof university === 'string' && university.trim() ? university.trim().slice(0, 120) : 'State University',
      typeof major === 'string' && major.trim() ? major.trim().slice(0, 120) : 'General Studies',
      typeof year_of_study === 'string' && year_of_study.trim() ? year_of_study.trim().slice(0, 40) : 'Year 1',
      alias
    );

  const userId = Number(result.lastInsertRowid);

  // Add an initial welcome companion message
  db.prepare(`
    INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source)
    VALUES (?, 'assistant', ?, 0, 'fallback')
  `).run(
    userId,
    `Welcome to MindMate, ${name.trim().split(' ')[0]}! Your private space is ready. Feel free to log a quick mood check-in, organize your study tasks, or chat here whenever academic stress builds up.`
  );

  const token = createSessionToken(userId, normalizedEmail);
  res.status(201).json({ token, user: getSafeUser(userId) });
});

app.post('/api/auth/login', (req, res) => {
  const { email, password } = req.body ?? {};
  if (typeof email !== 'string' || typeof password !== 'string') {
    res.status(400).json({ error: 'Email and password are required.' });
    return;
  }

  const normalizedEmail = email.trim().toLowerCase();
  const row = db
    .prepare('SELECT id, email, password_hash FROM users WHERE email = ?')
    .get(normalizedEmail) as { id: number; email: string; password_hash: string } | undefined;

  if (!row || !verifyPassword(password, row.password_hash)) {
    res.status(401).json({ error: 'Invalid email or password.' });
    return;
  }

  const token = createSessionToken(row.id, row.email);
  res.json({ token, user: getSafeUser(row.id) });
});

app.post('/api/auth/demo', (_req, res) => {
  const demo = db
    .prepare('SELECT id, email FROM users WHERE email = ?')
    .get('maya.patel@campus.edu') as { id: number; email: string } | undefined;

  if (!demo) {
    res.status(500).json({ error: 'Demo account is not initialized.' });
    return;
  }
  const token = createSessionToken(demo.id, demo.email);
  res.json({ token, user: getSafeUser(demo.id) });
});

app.get('/api/auth/me', requireAuth, (req: AuthenticatedRequest, res) => {
  const user = getSafeUser(req.user!.id);
  if (!user) {
    res.status(404).json({ error: 'User not found.' });
    return;
  }
  res.json({ user });
});

app.put('/api/auth/profile', requireAuth, (req: AuthenticatedRequest, res) => {
  const { name, university, major, year_of_study } = req.body ?? {};
  if (typeof name !== 'string' || name.trim().length < 2) {
    res.status(400).json({ error: 'Name must be at least 2 characters.' });
    return;
  }
  db.prepare(`
    UPDATE users SET name = ?, university = ?, major = ?, year_of_study = ? WHERE id = ?
  `).run(
    name.trim().slice(0, 80),
    typeof university === 'string' ? university.trim().slice(0, 120) : '',
    typeof major === 'string' ? major.trim().slice(0, 120) : '',
    typeof year_of_study === 'string' ? year_of_study.trim().slice(0, 40) : '',
    req.user!.id
  );
  res.json({ user: getSafeUser(req.user!.id) });
});

// ---------- MOOD CHECK-IN ROUTES ----------

app.get('/api/moods', requireAuth, (req: AuthenticatedRequest, res) => {
  const rows = db
    .prepare(`
      SELECT id, mood, stress_level, energy_level, note, created_at
      FROM mood_checkins
      WHERE user_id = ?
      ORDER BY datetime(created_at) DESC, id DESC
    `)
    .all(req.user!.id);
  res.json({ checkins: rows });
});

app.post('/api/moods', requireAuth, (req: AuthenticatedRequest, res) => {
  const { mood, stress_level, energy_level, note } = req.body ?? {};
  if (typeof mood !== 'string' || !ALLOWED_MOODS.includes(mood as (typeof ALLOWED_MOODS)[number])) {
    res.status(400).json({ error: 'Please select a valid mood option.' });
    return;
  }
  const stress = Number(stress_level);
  const energy = Number(energy_level);
  if (!Number.isInteger(stress) || stress < 1 || stress > 10 || !Number.isInteger(energy) || energy < 1 || energy > 10) {
    res.status(400).json({ error: 'Stress and energy levels must be whole numbers between 1 and 10.' });
    return;
  }
  const safeNote = typeof note === 'string' ? note.trim().slice(0, 500) : '';
  const nowIso = new Date().toISOString();

  const result = db
    .prepare(`
      INSERT INTO mood_checkins (user_id, mood, stress_level, energy_level, note, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `)
    .run(req.user!.id, mood, stress, energy, safeNote, nowIso);

  const created = db
    .prepare('SELECT id, mood, stress_level, energy_level, note, created_at FROM mood_checkins WHERE id = ?')
    .get(Number(result.lastInsertRowid));
  res.status(201).json({ checkin: created });
});

app.delete('/api/moods/:id', requireAuth, (req: AuthenticatedRequest, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: 'Invalid check-in ID.' });
    return;
  }
  const info = db.prepare('DELETE FROM mood_checkins WHERE id = ? AND user_id = ?').run(id, req.user!.id);
  if (info.changes === 0) {
    res.status(404).json({ error: 'Mood check-in not found.' });
    return;
  }
  res.json({ deleted: true });
});

// ---------- STUDY PLANNER ROUTES ----------

app.get('/api/tasks', requireAuth, (req: AuthenticatedRequest, res) => {
  const rows = db
    .prepare(`
      SELECT id, subject, title, description, deadline, priority, scheduled_slot, completed, created_at
      FROM study_tasks
      WHERE user_id = ?
      ORDER BY completed ASC, deadline ASC, id DESC
    `)
    .all(req.user!.id);
  res.json({ tasks: rows });
});

app.post('/api/tasks', requireAuth, (req: AuthenticatedRequest, res) => {
  const { subject, title, description, deadline, priority, scheduled_slot } = req.body ?? {};
  if (typeof subject !== 'string' || !subject.trim() || typeof title !== 'string' || !title.trim()) {
    res.status(400).json({ error: 'Subject and task title are required.' });
    return;
  }
  const safePriority =
    typeof priority === 'string' && ALLOWED_PRIORITIES.includes(priority as (typeof ALLOWED_PRIORITIES)[number])
      ? priority
      : 'medium';
  const safeDeadline =
    typeof deadline === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(deadline)
      ? deadline
      : new Date().toISOString().slice(0, 10);
  const safeSlot =
    typeof scheduled_slot === 'string' && scheduled_slot.trim()
      ? scheduled_slot.trim().slice(0, 60)
      : 'Morning (09:00 - 11:00)';

  const result = db
    .prepare(`
      INSERT INTO study_tasks (user_id, subject, title, description, deadline, priority, scheduled_slot)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `)
    .run(
      req.user!.id,
      subject.trim().slice(0, 80),
      title.trim().slice(0, 120),
      typeof description === 'string' ? description.trim().slice(0, 500) : '',
      safeDeadline,
      safePriority,
      safeSlot
    );

  const created = db
    .prepare(
      'SELECT id, subject, title, description, deadline, priority, scheduled_slot, completed, created_at FROM study_tasks WHERE id = ?'
    )
    .get(Number(result.lastInsertRowid));
  res.status(201).json({ task: created });
});

app.put('/api/tasks/:id', requireAuth, (req: AuthenticatedRequest, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: 'Invalid task ID.' });
    return;
  }
  const existing = db
    .prepare('SELECT * FROM study_tasks WHERE id = ? AND user_id = ?')
    .get(id, req.user!.id) as Record<string, unknown> | undefined;
  if (!existing) {
    res.status(404).json({ error: 'Study task not found.' });
    return;
  }

  const { subject, title, description, deadline, priority, scheduled_slot, completed } = req.body ?? {};
  const nextSubject = typeof subject === 'string' && subject.trim() ? subject.trim().slice(0, 80) : String(existing.subject);
  const nextTitle = typeof title === 'string' && title.trim() ? title.trim().slice(0, 120) : String(existing.title);
  const nextDesc = typeof description === 'string' ? description.trim().slice(0, 500) : String(existing.description);
  const nextDeadline =
    typeof deadline === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(deadline) ? deadline : String(existing.deadline);
  const nextPriority =
    typeof priority === 'string' && ALLOWED_PRIORITIES.includes(priority as (typeof ALLOWED_PRIORITIES)[number])
      ? priority
      : String(existing.priority);
  const nextSlot =
    typeof scheduled_slot === 'string' && scheduled_slot.trim()
      ? scheduled_slot.trim().slice(0, 60)
      : String(existing.scheduled_slot);
  const nextCompleted = typeof completed === 'boolean' || typeof completed === 'number' ? (completed ? 1 : 0) : Number(existing.completed);

  db.prepare(`
    UPDATE study_tasks
    SET subject = ?, title = ?, description = ?, deadline = ?, priority = ?, scheduled_slot = ?, completed = ?
    WHERE id = ? AND user_id = ?
  `).run(nextSubject, nextTitle, nextDesc, nextDeadline, nextPriority, nextSlot, nextCompleted, id, req.user!.id);

  const updated = db
    .prepare(
      'SELECT id, subject, title, description, deadline, priority, scheduled_slot, completed, created_at FROM study_tasks WHERE id = ?'
    )
    .get(id);
  res.json({ task: updated });
});

app.delete('/api/tasks/:id', requireAuth, (req: AuthenticatedRequest, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: 'Invalid task ID.' });
    return;
  }
  const info = db.prepare('DELETE FROM study_tasks WHERE id = ? AND user_id = ?').run(id, req.user!.id);
  if (info.changes === 0) {
    res.status(404).json({ error: 'Study task not found.' });
    return;
  }
  res.json({ deleted: true });
});

// ---------- POMODORO FOCUS ROUTES ----------

app.get('/api/focus', requireAuth, (req: AuthenticatedRequest, res) => {
  const sessions = db
    .prepare(`
      SELECT id, mode, duration_minutes, subject, completed_at
      FROM focus_sessions
      WHERE user_id = ?
      ORDER BY datetime(completed_at) DESC, id DESC
      LIMIT 30
    `)
    .all(req.user!.id);
  res.json({ sessions });
});

app.post('/api/focus', requireAuth, (req: AuthenticatedRequest, res) => {
  const { mode, duration_minutes, subject } = req.body ?? {};
  const safeMode = mode === 'short_break' || mode === 'long_break' ? mode : 'focus';
  const duration = Number(duration_minutes);
  if (!Number.isInteger(duration) || duration < 1 || duration > 120) {
    res.status(400).json({ error: 'Duration must be between 1 and 120 minutes.' });
    return;
  }
  const safeSubject = typeof subject === 'string' && subject.trim() ? subject.trim().slice(0, 80) : 'General Study';
  const nowIso = new Date().toISOString();

  const result = db
    .prepare(`
      INSERT INTO focus_sessions (user_id, mode, duration_minutes, subject, completed_at)
      VALUES (?, ?, ?, ?, ?)
    `)
    .run(req.user!.id, safeMode, duration, safeSubject, nowIso);

  const created = db
    .prepare('SELECT id, mode, duration_minutes, subject, completed_at FROM focus_sessions WHERE id = ?')
    .get(Number(result.lastInsertRowid));
  res.status(201).json({ session: created });
});

// ---------- AI COMPANION CHAT ROUTES ----------

app.get('/api/chat', requireAuth, (req: AuthenticatedRequest, res) => {
  const messages = db
    .prepare(`
      SELECT id, role, content, crisis_flagged, source, created_at
      FROM chat_messages
      WHERE user_id = ?
      ORDER BY id ASC
    `)
    .all(req.user!.id);
  res.json({ messages });
});

app.post('/api/chat', requireAuth, async (req: AuthenticatedRequest, res) => {
  const { message } = req.body ?? {};
  if (typeof message !== 'string' || !message.trim()) {
    res.status(400).json({ error: 'Please write a message to send.' });
    return;
  }
  const trimmed = message.trim().slice(0, 1500);
  const nowIso = new Date().toISOString();

  const user = db.prepare('SELECT name FROM users WHERE id = ?').get(req.user!.id) as { name: string } | undefined;
  const latestMoodRow = db
    .prepare('SELECT mood FROM mood_checkins WHERE user_id = ? ORDER BY datetime(created_at) DESC, id DESC LIMIT 1')
    .get(req.user!.id) as { mood: string } | undefined;
  const history = db
    .prepare('SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 10')
    .all(req.user!.id) as Array<{ role: string; content: string }>;
  history.reverse();

  const reply = await generateWellbeingReply({
    userMessage: trimmed,
    history,
    studentName: user?.name || 'Student',
    latestMood: latestMoodRow?.mood,
  });

  const userInsert = db
    .prepare(`
      INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source, created_at)
      VALUES (?, 'user', ?, ?, 'user', ?)
    `)
    .run(req.user!.id, trimmed, reply.crisisFlagged ? 1 : 0, nowIso);

  const assistantIso = new Date(Date.now() + 100).toISOString();
  const assistantInsert = db
    .prepare(`
      INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source, created_at)
      VALUES (?, 'assistant', ?, ?, ?, ?)
    `)
    .run(req.user!.id, reply.content, reply.crisisFlagged ? 1 : 0, reply.source, assistantIso);

  const userMsg = db.prepare('SELECT * FROM chat_messages WHERE id = ?').get(Number(userInsert.lastInsertRowid));
  const assistantMsg = db.prepare('SELECT * FROM chat_messages WHERE id = ?').get(Number(assistantInsert.lastInsertRowid));

  res.status(201).json({
    userMessage: userMsg,
    assistantMessage: assistantMsg,
    crisisFlagged: reply.crisisFlagged,
  });
});

app.delete('/api/chat', requireAuth, (req: AuthenticatedRequest, res) => {
  db.prepare('DELETE FROM chat_messages WHERE user_id = ?').run(req.user!.id);
  res.json({ cleared: true });
});

// ---------- PEER SUPPORT COMMUNITY ROUTES ----------

app.get('/api/community/posts', requireAuth, (req: AuthenticatedRequest, res) => {
  const posts = db
    .prepare(`
      SELECT p.id, p.user_id, p.author_alias, p.category, p.title, p.content, p.reported, p.created_at,
             (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.reaction_type = 'heart') AS heart_count,
             (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.reaction_type = 'helpful') AS helpful_count,
             (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.user_id = ? AND r.reaction_type = 'heart') AS user_hearted,
             (SELECT COUNT(*) FROM community_reactions r WHERE r.post_id = p.id AND r.user_id = ? AND r.reaction_type = 'helpful') AS user_helpful
      FROM community_posts p
      ORDER BY datetime(p.created_at) DESC, p.id DESC
    `)
    .all(req.user!.id, req.user!.id) as Array<Record<string, unknown>>;

  const comments = db
    .prepare(`
      SELECT id, post_id, author_alias, content, reported, created_at
      FROM community_comments
      ORDER BY id ASC
    `)
    .all() as Array<Record<string, unknown>>;

  const commentsByPost = new Map<number, Array<Record<string, unknown>>>();
  for (const c of comments) {
    const pid = Number(c.post_id);
    if (!commentsByPost.has(pid)) commentsByPost.set(pid, []);
    commentsByPost.get(pid)!.push(c);
  }

  const enriched = posts.map((p) => ({
    id: p.id,
    is_owner: Number(p.user_id) === req.user!.id,
    author_alias: p.author_alias,
    category: p.category,
    title: p.title,
    content: p.content,
    reported: Boolean(p.reported),
    created_at: p.created_at,
    heart_count: Number(p.heart_count || 0),
    helpful_count: Number(p.helpful_count || 0),
    user_hearted: Boolean(p.user_hearted),
    user_helpful: Boolean(p.user_helpful),
    comments: commentsByPost.get(Number(p.id)) || [],
  }));

  res.json({ posts: enriched });
});

app.post('/api/community/posts', requireAuth, (req: AuthenticatedRequest, res) => {
  const { category, title, content } = req.body ?? {};
  if (typeof title !== 'string' || title.trim().length < 3 || typeof content !== 'string' || content.trim().length < 8) {
    res.status(400).json({ error: 'Please include a clear title (3+ chars) and message (8+ chars).' });
    return;
  }
  const safeCat =
    typeof category === 'string' && ALLOWED_CATEGORIES.includes(category as (typeof ALLOWED_CATEGORIES)[number])
      ? category
      : 'Academic Stress';

  const user = db
    .prepare('SELECT name, community_alias, privacy_anonymous_community FROM users WHERE id = ?')
    .get(req.user!.id) as { name: string; community_alias: string; privacy_anonymous_community: number };

  const displayAlias = user.privacy_anonymous_community ? user.community_alias : user.name.split(' ')[0];
  const nowIso = new Date().toISOString();

  const result = db
    .prepare(`
      INSERT INTO community_posts (user_id, author_alias, category, title, content, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `)
    .run(req.user!.id, displayAlias, safeCat, title.trim().slice(0, 120), content.trim().slice(0, 1000), nowIso);

  res.status(201).json({ id: Number(result.lastInsertRowid) });
});

app.post('/api/community/posts/:id/react', requireAuth, (req: AuthenticatedRequest, res) => {
  const postId = Number(req.params.id);
  const { reaction_type } = req.body ?? {};
  if (!Number.isInteger(postId) || (reaction_type !== 'heart' && reaction_type !== 'helpful')) {
    res.status(400).json({ error: 'Invalid post or reaction type.' });
    return;
  }

  const existing = db
    .prepare('SELECT id FROM community_reactions WHERE post_id = ? AND user_id = ? AND reaction_type = ?')
    .get(postId, req.user!.id, reaction_type) as { id: number } | undefined;

  if (existing) {
    db.prepare('DELETE FROM community_reactions WHERE id = ?').run(existing.id);
    res.json({ active: false });
  } else {
    db.prepare('INSERT INTO community_reactions (post_id, user_id, reaction_type) VALUES (?, ?, ?)').run(
      postId,
      req.user!.id,
      reaction_type
    );
    res.json({ active: true });
  }
});

app.post('/api/community/posts/:id/comments', requireAuth, (req: AuthenticatedRequest, res) => {
  const postId = Number(req.params.id);
  const { content } = req.body ?? {};
  if (!Number.isInteger(postId) || typeof content !== 'string' || content.trim().length < 2) {
    res.status(400).json({ error: 'Comment cannot be empty.' });
    return;
  }

  const postExists = db.prepare('SELECT id FROM community_posts WHERE id = ?').get(postId);
  if (!postExists) {
    res.status(404).json({ error: 'Post not found.' });
    return;
  }

  const user = db
    .prepare('SELECT name, community_alias, privacy_anonymous_community FROM users WHERE id = ?')
    .get(req.user!.id) as { name: string; community_alias: string; privacy_anonymous_community: number };

  const displayAlias = user.privacy_anonymous_community ? user.community_alias : user.name.split(' ')[0];
  const nowIso = new Date().toISOString();

  db.prepare(`
    INSERT INTO community_comments (post_id, user_id, author_alias, content, created_at)
    VALUES (?, ?, ?, ?, ?)
  `).run(postId, req.user!.id, displayAlias, content.trim().slice(0, 500), nowIso);

  res.status(201).json({ added: true });
});

app.post('/api/community/posts/:id/report', requireAuth, (req: AuthenticatedRequest, res) => {
  const postId = Number(req.params.id);
  const { reason } = req.body ?? {};
  if (!Number.isInteger(postId)) {
    res.status(400).json({ error: 'Invalid post ID.' });
    return;
  }
  const safeReason = typeof reason === 'string' && reason.trim() ? reason.trim().slice(0, 200) : 'Flagged for review';
  db.prepare('UPDATE community_posts SET reported = 1, report_reason = ? WHERE id = ?').run(safeReason, postId);
  res.json({ reported: true });
});

app.delete('/api/community/posts/:id', requireAuth, (req: AuthenticatedRequest, res) => {
  const postId = Number(req.params.id);
  if (!Number.isInteger(postId)) {
    res.status(400).json({ error: 'Invalid post ID.' });
    return;
  }
  const info = db.prepare('DELETE FROM community_posts WHERE id = ? AND user_id = ?').run(postId, req.user!.id);
  if (info.changes === 0) {
    res.status(403).json({ error: 'You can only delete your own posts.' });
    return;
  }
  res.json({ deleted: true });
});

// ---------- ANALYTICS ROUTES ----------

app.get('/api/analytics', requireAuth, (req: AuthenticatedRequest, res) => {
  const userId = req.user!.id;

  const checkins = db
    .prepare(`
      SELECT mood, stress_level, energy_level, created_at
      FROM mood_checkins
      WHERE user_id = ?
      ORDER BY datetime(created_at) ASC
    `)
    .all(userId) as Array<{ mood: string; stress_level: number; energy_level: number; created_at: string }>;

  const tasks = db
    .prepare('SELECT priority, completed FROM study_tasks WHERE user_id = ?')
    .all(userId) as Array<{ priority: string; completed: number }>;

  const focusSessions = db
    .prepare(`
      SELECT mode, duration_minutes, subject, completed_at
      FROM focus_sessions
      WHERE user_id = ? AND mode = 'focus'
      ORDER BY datetime(completed_at) ASC
    `)
    .all(userId) as Array<{ mode: string; duration_minutes: number; subject: string; completed_at: string }>;

  // Weekly trend points (last 7 check-ins or grouped by day)
  const weeklyTrends = checkins.slice(-10).map((c) => ({
    date: new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    moodScore: MOOD_SCORES[c.mood] ?? 3,
    stress: c.stress_level,
    energy: c.energy_level,
    mood: c.mood,
  }));

  // Mood distribution
  const moodCounts = ALLOWED_MOODS.map((m) => ({
    mood: m,
    count: checkins.filter((c) => c.mood === m).length,
  }));

  // Focus sessions by last 7 days
  const focusByDayMap = new Map<string, { day: string; sessions: number; minutes: number }>();
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const label = d.toLocaleDateString('en-US', { weekday: 'short' });
    focusByDayMap.set(key, { day: label, sessions: 0, minutes: 0 });
  }
  for (const s of focusSessions) {
    const key = s.completed_at.slice(0, 10);
    const entry = focusByDayMap.get(key);
    if (entry) {
      entry.sessions += 1;
      entry.minutes += s.duration_minutes;
    }
  }

  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((t) => t.completed === 1).length;
  const completionRate = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  const avgStress =
    checkins.length > 0
      ? Number((checkins.reduce((sum, c) => sum + c.stress_level, 0) / checkins.length).toFixed(1))
      : 0;
  const avgEnergy =
    checkins.length > 0
      ? Number((checkins.reduce((sum, c) => sum + c.energy_level, 0) / checkins.length).toFixed(1))
      : 0;
  const totalFocusMinutes = focusSessions.reduce((sum, f) => sum + f.duration_minutes, 0);

  // Simple wellbeing insights derived from actual data
  const insights: string[] = [];
  if (checkins.length === 0) {
    insights.push('Log your first mood check-in to start seeing personalized stress and energy patterns.');
  } else {
    if (avgStress >= 6.5) {
      insights.push(
        `Your average stress level is ${avgStress}/10 across recent check-ins. Scheduling shorter 25-minute focus blocks with 5-minute breathing breaks may help lower tension.`
      );
    } else {
      insights.push(
        `Your recent stress average is steady at ${avgStress}/10 alongside ${avgEnergy}/10 average energy. Keep protecting your daily rest breaks.`
      );
    }

    const recent3 = checkins.slice(-3);
    const earlier3 = checkins.slice(-6, -3);
    if (recent3.length >= 2 && earlier3.length >= 2) {
      const recentAvg = recent3.reduce((s, x) => s + x.stress_level, 0) / recent3.length;
      const earlierAvg = earlier3.reduce((s, x) => s + x.stress_level, 0) / earlier3.length;
      if (recentAvg < earlierAvg - 0.5) {
        insights.push('Your recent stress trend has eased compared to earlier this week—your pacing is paying off.');
      } else if (recentAvg > earlierAvg + 0.5) {
        insights.push('Stress has ticked up slightly in your newest check-ins. Consider lighter evening study slots today.');
      }
    }
  }

  if (focusSessions.length > 0) {
    insights.push(
      `You have completed ${focusSessions.length} focus sessions (${totalFocusMinutes} mindful study minutes). Consistency beats marathon cramming.`
    );
  }
  if (totalTasks > 0) {
    insights.push(
      `You have completed ${completedTasks} of ${totalTasks} planned study tasks (${completionRate}% completion rate).`
    );
  }

  res.json({
    summary: {
      totalCheckins: checkins.length,
      avgStress,
      avgEnergy,
      totalTasks,
      completedTasks,
      completionRate,
      totalFocusSessions: focusSessions.length,
      totalFocusMinutes,
    },
    weeklyTrends,
    moodCounts,
    focusByDay: Array.from(focusByDayMap.values()),
    insights,
  });
});

// ---------- PRIVACY SETTINGS ROUTES ----------

app.get('/api/privacy', requireAuth, (req: AuthenticatedRequest, res) => {
  const prefs = db
    .prepare(`
      SELECT privacy_anonymous_community, privacy_include_insights, privacy_retention_days
      FROM users WHERE id = ?
    `)
    .get(req.user!.id);

  const counts = {
    moodCheckins: (
      db.prepare('SELECT COUNT(*) AS c FROM mood_checkins WHERE user_id = ?').get(req.user!.id) as { c: number }
    ).c,
    studyTasks: (
      db.prepare('SELECT COUNT(*) AS c FROM study_tasks WHERE user_id = ?').get(req.user!.id) as { c: number }
    ).c,
    chatMessages: (
      db.prepare('SELECT COUNT(*) AS c FROM chat_messages WHERE user_id = ?').get(req.user!.id) as { c: number }
    ).c,
    focusSessions: (
      db.prepare('SELECT COUNT(*) AS c FROM focus_sessions WHERE user_id = ?').get(req.user!.id) as { c: number }
    ).c,
  };

  res.json({ preferences: prefs, counts });
});

app.put('/api/privacy', requireAuth, (req: AuthenticatedRequest, res) => {
  const { privacy_anonymous_community, privacy_include_insights, privacy_retention_days } = req.body ?? {};
  const anon = privacy_anonymous_community ? 1 : 0;
  const insights = privacy_include_insights ? 1 : 0;
  const retention = [30, 90, 180, 365].includes(Number(privacy_retention_days))
    ? Number(privacy_retention_days)
    : 90;

  db.prepare(`
    UPDATE users
    SET privacy_anonymous_community = ?, privacy_include_insights = ?, privacy_retention_days = ?
    WHERE id = ?
  `).run(anon, insights, retention, req.user!.id);

  res.json({
    preferences: {
      privacy_anonymous_community: anon,
      privacy_include_insights: insights,
      privacy_retention_days: retention,
    },
  });
});

app.get('/api/privacy/export', requireAuth, (req: AuthenticatedRequest, res) => {
  const user = getSafeUser(req.user!.id);
  const moodCheckins = db
    .prepare('SELECT mood, stress_level, energy_level, note, created_at FROM mood_checkins WHERE user_id = ?')
    .all(req.user!.id);
  const studyTasks = db
    .prepare('SELECT subject, title, description, deadline, priority, scheduled_slot, completed FROM study_tasks WHERE user_id = ?')
    .all(req.user!.id);
  const focusSessions = db
    .prepare('SELECT mode, duration_minutes, subject, completed_at FROM focus_sessions WHERE user_id = ?')
    .all(req.user!.id);

  res.json({
    exportedAt: new Date().toISOString(),
    profile: user,
    moodCheckins,
    studyTasks,
    focusSessions,
  });
});

app.delete('/api/privacy/data', requireAuth, (req: AuthenticatedRequest, res) => {
  const scope = req.query.scope;
  if (scope === 'moods') {
    db.prepare('DELETE FROM mood_checkins WHERE user_id = ?').run(req.user!.id);
  } else if (scope === 'chat') {
    db.prepare('DELETE FROM chat_messages WHERE user_id = ?').run(req.user!.id);
  } else if (scope === 'all') {
    db.prepare('DELETE FROM mood_checkins WHERE user_id = ?').run(req.user!.id);
    db.prepare('DELETE FROM chat_messages WHERE user_id = ?').run(req.user!.id);
    db.prepare('DELETE FROM focus_sessions WHERE user_id = ?').run(req.user!.id);
  } else {
    res.status(400).json({ error: 'Specify a valid scope (moods, chat, or all).' });
    return;
  }
  res.json({ deleted: true, scope });
});

// ---------- COUNSELLING & SUPPORT ROUTES ----------

app.get('/api/support/counsellors', requireAuth, (req: AuthenticatedRequest, res) => {
  const requests = db
    .prepare(`
      SELECT id, counsellor_name, preferred_slot, topic, status, created_at
      FROM counsellor_requests
      WHERE user_id = ?
      ORDER BY id DESC
    `)
    .all(req.user!.id);

  const counsellors = [
    {
      id: 'c1',
      name: 'Dr. Ananya Rao',
      role: 'Lead Campus Wellbeing Counsellor',
      focus: 'Academic Stress · Exam Anxiety · Adjustment',
      office: 'Student Wellness Wing, Room 204',
      hours: 'Mon – Fri, 09:00 AM – 05:00 PM',
      contactEmail: 'wellness-office@campus.example.edu',
      phone: '+1 (555) 234-8910',
    },
    {
      id: 'c2',
      name: 'Marcus Bennett, LCSW',
      role: 'Graduate & Postgraduate Support Specialist',
      focus: 'Burnout Recovery · Thesis Pressure · Work-Life Balance',
      office: 'Student Wellness Wing, Room 208',
      hours: 'Tue – Sat, 10:00 AM – 06:00 PM',
      contactEmail: 'grad-support@campus.example.edu',
      phone: '+1 (555) 234-8914',
    },
    {
      id: 'c3',
      name: 'Priya Nair, M.Sc.',
      role: 'Peer & Mindfulness Coordinator',
      focus: 'Homesickness · Peer Connection · Relaxation Coaching',
      office: 'Campus Union Suite 112',
      hours: 'Mon – Thu, 11:00 AM – 06:30 PM',
      contactEmail: 'peer-care@campus.example.edu',
      phone: '+1 (555) 234-8922',
    },
  ];

  res.json({ counsellors, requests });
});

app.post('/api/support/request', requireAuth, (req: AuthenticatedRequest, res) => {
  const { counsellor_name, preferred_slot, topic, consent_given } = req.body ?? {};
  if (!consent_given) {
    res.status(400).json({ error: 'Explicit student consent is required before submitting a support request.' });
    return;
  }
  if (typeof counsellor_name !== 'string' || !counsellor_name.trim() || typeof preferred_slot !== 'string' || !preferred_slot.trim()) {
    res.status(400).json({ error: 'Please choose a counsellor and preferred time slot.' });
    return;
  }

  const result = db
    .prepare(`
      INSERT INTO counsellor_requests (user_id, counsellor_name, preferred_slot, topic, consent_given, status)
      VALUES (?, ?, ?, ?, 1, 'Consent Recorded · Ready for Confirmation')
    `)
    .run(
      req.user!.id,
      counsellor_name.trim().slice(0, 100),
      preferred_slot.trim().slice(0, 80),
      typeof topic === 'string' && topic.trim() ? topic.trim().slice(0, 300) : 'General student wellbeing check-in'
    );

  const created = db
    .prepare('SELECT id, counsellor_name, preferred_slot, topic, status, created_at FROM counsellor_requests WHERE id = ?')
    .get(Number(result.lastInsertRowid));
  res.status(201).json({ request: created });
});

// ---------- SERVER STARTUP (VITE DEV / PROD STATIC) ----------

async function startServer() {
  const PORT = Number(process.env.PORT) || 3000;

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distDir = path.resolve(process.cwd(), 'dist');
    if (fs.existsSync(distDir)) {
      app.use(express.static(distDir));
      app.get('*', (_req, res) => {
        res.sendFile(path.join(distDir, 'index.html'));
      });
    }
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`MINDMATE server running on http://localhost:${PORT}`);
  });
}

startServer();
