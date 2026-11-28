import Database from 'better-sqlite3';
import path from 'path';
import { hashPassword } from './auth.ts';

const dbPath = process.env.DATABASE_PATH
  ? path.resolve(process.cwd(), process.env.DATABASE_PATH)
  : path.resolve(process.cwd(), 'mindmate.db');

export const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

export function initDatabase(): void {
  db.exec(`
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
  `);

  seedInitialData();
}

function daysAgoIso(daysAgo: number, hour = 10): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, 15, 0, 0);
  return d.toISOString();
}

function daysAheadDate(daysAhead: number): string {
  const d = new Date();
  d.setDate(d.getDate() + daysAhead);
  return d.toISOString().slice(0, 10);
}

function seedInitialData(): void {
  const existingDemo = db
    .prepare('SELECT id FROM users WHERE email = ?')
    .get('maya.patel@campus.edu') as { id: number } | undefined;

  if (existingDemo) return;

  const insertUser = db.prepare(`
    INSERT INTO users (name, email, password_hash, university, major, year_of_study, community_alias, is_demo)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const demoResult = insertUser.run(
    'Maya Patel',
    'maya.patel@campus.edu',
    hashPassword('MindMate2026!'),
    'Crestwood Institute of Technology',
    'Master of Computer Applications (MCA)',
    'Final Year',
    'Calm Maple #108',
    1
  );
  const demoId = Number(demoResult.lastInsertRowid);

  // Seed a couple of peer accounts for realistic community posts (never exposed with PII)
  const peer1Id = Number(
    insertUser.run(
      'Peer One',
      'peer1@internal.local',
      hashPassword('InternalPeerPass1!'),
      'Crestwood Institute of Technology',
      'Data Science',
      'Year 1',
      'Quiet Cedar #342',
      0
    ).lastInsertRowid
  );
  const peer2Id = Number(
    insertUser.run(
      'Peer Two',
      'peer2@internal.local',
      hashPassword('InternalPeerPass2!'),
      'Crestwood Institute of Technology',
      'Psychology',
      'Year 3',
      'Gentle Fern #519',
      0
    ).lastInsertRowid
  );

  // Seed 8 days of mood check-ins for Maya
  const insertMood = db.prepare(`
    INSERT INTO mood_checkins (user_id, mood, stress_level, energy_level, note, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  const moodSeed = [
    { days: 7, mood: 'Stressed', stress: 8, energy: 4, note: 'Two project milestones due in the same week.' },
    { days: 6, mood: 'Anxious', stress: 7, energy: 5, note: 'Worried about upcoming seminar presentation.' },
    { days: 5, mood: 'Neutral', stress: 5, energy: 6, note: 'Broke the assignment into smaller tasks, felt steadier.' },
    { days: 4, mood: 'Calm', stress: 4, energy: 7, note: 'Walked outside for 20 minutes between lectures.' },
    { days: 3, mood: 'Happy', stress: 3, energy: 8, note: 'Finished database schema ahead of schedule!' },
    { days: 2, mood: 'Calm', stress: 4, energy: 7, note: 'Good sleep last night and steady study pace.' },
    { days: 1, mood: 'Stressed', stress: 6, energy: 5, note: 'Late evening debugging session made me tired.' },
    { days: 0, mood: 'Calm', stress: 4, energy: 7, note: 'Morning breathing exercise helped me start focused.' },
  ];
  for (const m of moodSeed) {
    insertMood.run(demoId, m.mood, m.stress, m.energy, m.note, daysAgoIso(m.days, 9));
  }

  // Seed study tasks
  const insertTask = db.prepare(`
    INSERT INTO study_tasks (user_id, subject, title, description, deadline, priority, scheduled_slot, completed)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);
  insertTask.run(
    demoId,
    'Algorithms & Complexity',
    'Dynamic Programming Problem Set 4',
    'Complete memoization proofs and time-complexity analysis for 5 problems.',
    daysAheadDate(1),
    'high',
    'Morning (09:00 - 11:00)',
    0
  );
  insertTask.run(
    demoId,
    'Database Systems',
    'Review B+ Tree Indexing & Normalization',
    'Summarize 3NF and BCNF examples for Friday quiz.',
    daysAheadDate(2),
    'medium',
    'Afternoon (14:00 - 16:00)',
    0
  );
  insertTask.run(
    demoId,
    'Cloud Architecture',
    'Draft Microservices Resilience Notes',
    'Outline circuit breaker and retry patterns with diagrams.',
    daysAheadDate(4),
    'low',
    'Evening (18:30 - 20:00)',
    0
  );
  insertTask.run(
    demoId,
    'MCA Capstone Project',
    'Prepare Usability Testing Script',
    'Write 5 scenario prompts for peer walkthrough session.',
    daysAheadDate(0),
    'high',
    'Afternoon (14:00 - 16:00)',
    1
  );
  insertTask.run(
    demoId,
    'Research Methodology',
    'Annotate 3 Wellbeing Literature Papers',
    'Extract sample size and ethical privacy protocols.',
    daysAheadDate(-1),
    'medium',
    'Morning (09:00 - 11:00)',
    1
  );

  // Seed Pomodoro focus sessions across the past week
  const insertFocus = db.prepare(`
    INSERT INTO focus_sessions (user_id, mode, duration_minutes, subject, completed_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  const focusSeed = [
    { days: 6, mins: 25, subject: 'Algorithms & Complexity' },
    { days: 5, mins: 25, subject: 'Database Systems' },
    { days: 5, mins: 25, subject: 'Database Systems' },
    { days: 4, mins: 25, subject: 'MCA Capstone Project' },
    { days: 3, mins: 25, subject: 'Cloud Architecture' },
    { days: 2, mins: 25, subject: 'Algorithms & Complexity' },
    { days: 2, mins: 25, subject: 'Algorithms & Complexity' },
    { days: 1, mins: 25, subject: 'Research Methodology' },
    { days: 0, mins: 25, subject: 'MCA Capstone Project' },
  ];
  for (const f of focusSeed) {
    insertFocus.run(demoId, 'focus', f.mins, f.subject, daysAgoIso(f.days, 15));
  }

  // Seed welcome AI companion exchange
  const insertChat = db.prepare(`
    INSERT INTO chat_messages (user_id, role, content, crisis_flagged, source, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  insertChat.run(
    demoId,
    'assistant',
    "Hi Maya, I'm MindMate—your private wellbeing companion. Whether you're juggling deadlines, feeling worn out, or just want to organize a calmer study plan today, I'm here to listen without judgment. How is your day feeling so far?",
    0,
    'fallback',
    daysAgoIso(0, 8)
  );

  // Seed community posts (privacy-safe anonymous aliases)
  const insertPost = db.prepare(`
    INSERT INTO community_posts (user_id, author_alias, category, title, content, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  const post1Id = Number(
    insertPost.run(
      peer1Id,
      'Quiet Cedar #342',
      'Academic Stress',
      'How I stopped spiralling before my Algorithms midterm',
      'Last week I had three chapters left and felt completely frozen. Switching to one 25-minute Pomodoro just to outline key formulas broke the paralysis. Sharing in case someone else feels stuck tonight—start ridiculously small.',
      daysAgoIso(2, 19)
    ).lastInsertRowid
  );
  const post2Id = Number(
    insertPost.run(
      peer2Id,
      'Gentle Fern #519',
      'Small Wins',
      'Actually closed my laptop at 9 PM for the first time this semester',
      'Used to stay up staring at notes until 1 AM with zero retention. Tried a 10-minute wind-down stretch and slept 7.5 hours. Woke up way sharper for my morning lab.',
      daysAgoIso(1, 11)
    ).lastInsertRowid
  );
  const post3Id = Number(
    insertPost.run(
      demoId,
      'Calm Maple #108',
      'Study Tips',
      '20-20-20 eye break rule during long coding sessions',
      'Every 20 minutes I look at a tree outside my dorm window 20 feet away for 20 seconds. My afternoon headaches disappeared within three days.',
      daysAgoIso(0, 10)
    ).lastInsertRowid
  );

  const insertComment = db.prepare(`
    INSERT INTO community_comments (post_id, user_id, author_alias, content, created_at)
    VALUES (?, ?, ?, ?, ?)
  `);
  insertComment.run(
    post1Id,
    peer2Id,
    'Gentle Fern #519',
    'Starting small is everything. Even writing the title of a doc counts as momentum.',
    daysAgoIso(2, 20)
  );
  insertComment.run(
    post2Id,
    demoId,
    'Calm Maple #108',
    'Protecting sleep really beats late-night cramming every time. Happy for you!',
    daysAgoIso(1, 13)
  );

  const insertReaction = db.prepare(`
    INSERT INTO community_reactions (post_id, user_id, reaction_type)
    VALUES (?, ?, ?)
  `);
  insertReaction.run(post1Id, peer2Id, 'helpful');
  insertReaction.run(post1Id, demoId, 'heart');
  insertReaction.run(post2Id, peer1Id, 'heart');
  insertReaction.run(post3Id, peer1Id, 'helpful');
}
