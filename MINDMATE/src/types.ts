export type PageId =
  | 'landing'
  | 'auth'
  | 'dashboard'
  | 'mood'
  | 'companion'
  | 'planner'
  | 'pomodoro'
  | 'toolkit'
  | 'community'
  | 'analytics'
  | 'support'
  | 'privacy';

export type MoodOption = 'Happy' | 'Calm' | 'Neutral' | 'Stressed' | 'Sad' | 'Anxious';

export interface User {
  id: number;
  name: string;
  email: string;
  university: string;
  major: string;
  year_of_study: string;
  community_alias: string;
  is_demo: number;
  privacy_anonymous_community: number;
  privacy_include_insights: number;
  privacy_retention_days: number;
  created_at: string;
}

export interface MoodCheckin {
  id: number;
  mood: MoodOption;
  stress_level: number;
  energy_level: number;
  note: string;
  created_at: string;
}

export interface StudyTask {
  id: number;
  subject: string;
  title: string;
  description: string;
  deadline: string;
  priority: 'low' | 'medium' | 'high';
  scheduled_slot: string;
  completed: number;
  created_at: string;
}

export interface FocusSession {
  id: number;
  mode: 'focus' | 'short_break' | 'long_break';
  duration_minutes: number;
  subject: string;
  completed_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  crisis_flagged: number;
  source: string;
  created_at: string;
}

export interface CommunityComment {
  id: number;
  post_id: number;
  author_alias: string;
  content: string;
  reported: number;
  created_at: string;
}

export interface CommunityPost {
  id: number;
  is_owner: boolean;
  author_alias: string;
  category: string;
  title: string;
  content: string;
  reported: boolean;
  created_at: string;
  heart_count: number;
  helpful_count: number;
  user_hearted: boolean;
  user_helpful: boolean;
  comments: CommunityComment[];
}

export interface AnalyticsData {
  summary: {
    totalCheckins: number;
    avgStress: number;
    avgEnergy: number;
    totalTasks: number;
    completedTasks: number;
    completionRate: number;
    totalFocusSessions: number;
    totalFocusMinutes: number;
  };
  weeklyTrends: Array<{
    date: string;
    moodScore: number;
    stress: number;
    energy: number;
    mood: string;
  }>;
  moodCounts: Array<{
    mood: string;
    count: number;
  }>;
  focusByDay: Array<{
    day: string;
    sessions: number;
    minutes: number;
  }>;
  insights: string[];
}

export interface Counsellor {
  id: string;
  name: string;
  role: string;
  focus: string;
  office: string;
  hours: string;
  contactEmail: string;
  phone: string;
}

export interface CounsellorRequest {
  id: number;
  counsellor_name: string;
  preferred_slot: string;
  topic: string;
  status: string;
  created_at: string;
}
