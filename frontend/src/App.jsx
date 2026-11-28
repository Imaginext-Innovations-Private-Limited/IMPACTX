
import { useEffect, useState } from "react";
import axios from "axios";
import Auth from "./Auth";
import AIAssistant from "./AIAssistant";
import PeerSupport from "./PeerSupport";
import Counselling from "./Counselling";
import AdminLogin from "./AdminLogin";
import AdminDashboard from "./AdminDashboard";
import Notifications from "./Notifications";

import {
  Heart, LayoutDashboard, Brain, BookOpen, CalendarDays,
  Users, HandHeart, Bell, Search, Sparkles,
  Sun, Moon, Coffee, Droplets, Clock, ArrowUpRight,
  CheckCircle2, Flame, ChevronRight, Menu, X,
  MessageCircle, ShieldCheck
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, Tooltip
} from "recharts";
import "./App.css";

const API = "http://localhost:5000/api";

const moodData = [
  { day: "Mon", mood: 65 },
  { day: "Tue", mood: 75 },
  { day: "Wed", mood: 55 },
  { day: "Thu", mood: 85 },
  { day: "Fri", mood: 70 },
  { day: "Sat", mood: 90 },
  { day: "Sun", mood: 80 }
];

const initialTasks = [
  { id: 1, title: "Complete Data Analytics assignment", time: "10:00 AM", done: true },
  { id: 2, title: "Study Database Management", time: "12:30 PM", done: false },
  { id: 3, title: "Revise Machine Learning notes", time: "03:00 PM", done: false }
];

const navigation = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Mood Tracker", icon: Brain },
  { name: "Study Planner", icon: BookOpen },
  { name: "Reminders", icon: CalendarDays },
  { name: "AI Assistant", icon: Sparkles },
  { name: "Peer Support", icon: Users },
  { name: "Counselling", icon: HandHeart },
    { name: "Notifications", icon: Bell }

];

const moodEmojis = {
  Amazing: "😄",
  Good: "🙂",
  Okay: "😐",
  Stressed: "😟",
  Low: "😔"
};

function App() {
const [user, setUser] = useState(null);
const [admin, setAdmin] = useState(null);
const [authChecked, setAuthChecked] = useState(false);
const [authMode, setAuthMode] = useState("student");
  const [active, setActive] = useState("Dashboard");

  const [mood, setMood] = useState("");
  const [tasks, setTasks] = useState(initialTasks);

  const [studyTasks, setStudyTasks] = useState([]);
  const [studyLoading, setStudyLoading] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskDate, setNewTaskDate] = useState("");
  const [newTaskTime, setNewTaskTime] = useState("");

  const [moodHistory, setMoodHistory] = useState([]);
  const [moodLoading, setMoodLoading] = useState(false);

  const [menuOpen, setMenuOpen] = useState(false);
  const [notice, setNotice] = useState("");

  const [reminders, setReminders] = useState([]);
  const [reminderLoading, setReminderLoading] = useState(false);
  const [reminderTitle, setReminderTitle] = useState("");
  const [reminderDescription, setReminderDescription] = useState("");
  const [reminderDate, setReminderDate] = useState("");
  const [reminderTime, setReminderTime] = useState("");

  // Check student login
  // Check existing admin or student session
useEffect(() => {
  const checkSession = async () => {
    try {
      const results = await Promise.allSettled([
        axios.get(`${API}/admin/me`, {
          withCredentials: true
        }),
        axios.get(`${API}/auth/me`, {
          withCredentials: true
        })
      ]);

      const adminResult = results[0];
      const studentResult = results[1];

      if (adminResult.status === "fulfilled") {
        setAdmin(adminResult.value.data.admin);
        setUser(null);
      } else if (studentResult.status === "fulfilled") {
        setUser(studentResult.value.data.student);
        setAdmin(null);
      } else {
        setUser(null);
        setAdmin(null);
      }
    } finally {
      setAuthChecked(true);
    }
  };

  checkSession();
}, []);
  // Load mood history
  useEffect(() => {
    if (!user || active !== "Mood Tracker") return;

    const fetchMoodHistory = async () => {
      setMoodLoading(true);
      try {
        const response = await axios.get(`${API}/mood/`, {
          withCredentials: true
        });
        setMoodHistory(response.data.moods || []);
      } catch (error) {
        setNotice(error.response?.data?.message || "Unable to load mood history.");
      } finally {
        setMoodLoading(false);
      }
    };

    fetchMoodHistory();
  }, [active, user]);

  // Load study tasks
  useEffect(() => {
    if (!user || active !== "Study Planner") return;

    const fetchStudyTasks = async () => {
      setStudyLoading(true);
      try {
        const response = await axios.get(`${API}/study/`, {
          withCredentials: true
        });
        setStudyTasks(response.data.tasks || []);
      } catch (error) {
        setNotice(error.response?.data?.message || "Unable to load study tasks.");
      } finally {
        setStudyLoading(false);
      }
    };

    fetchStudyTasks();
  }, [active, user]);

  // Load reminders
  useEffect(() => {
    if (!user || active !== "Reminders") return;

    const fetchReminders = async () => {
      setReminderLoading(true);
      try {
        const response = await axios.get(`${API}/reminders/`, {
          withCredentials: true
        });
        setReminders(response.data.reminders || []);
      } catch (error) {
        setNotice(error.response?.data?.message || "Unable to load reminders.");
      } finally {
        setReminderLoading(false);
      }
    };

    fetchReminders();
  }, [active, user]);

  // Logout
  const handleLogout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, {
        withCredentials: true
      });

      setUser(null);
      setActive("Dashboard");
      setMoodHistory([]);
      setStudyTasks([]);
      setReminders([]);
    } catch {
      alert("Unable to log out. Please try again.");
    }
  };

  const completed = tasks.filter(task => task.done).length;
  const studyCompleted = studyTasks.filter(task => Boolean(task.is_completed)).length;
  const studyRemaining = studyTasks.length - studyCompleted;

  // Dashboard task toggle
  const toggleTask = (id) => {
    setTasks(old => old.map(task =>
      task.id === id ? { ...task, done: !task.done } : task
    ));
  };

  // Save mood
  const selectMood = async (value) => {
    try {
      const response = await axios.post(
        `${API}/mood/`,
        { mood: value },
        { withCredentials: true }
      );

      setMood(value);
      setNotice(response.data.message || "Your mood check-in was saved!");
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to save your mood. Please try again.");
    }
  };

  // Add study task
  const addStudyTask = async (e) => {
    e.preventDefault();

    if (!newTaskTitle.trim() || !newTaskDate || !newTaskTime) {
      setNotice("Please fill in all task details.");
      return;
    }

    try {
      const response = await axios.post(
        `${API}/study/`,
        {
          title: newTaskTitle.trim(),
          task_date: newTaskDate,
          task_time: newTaskTime
        },
        { withCredentials: true }
      );

      setNewTaskTitle("");
      setNewTaskDate("");
      setNewTaskTime("");
      setNotice(response.data.message || "Study task added successfully!");

      const updated = await axios.get(`${API}/study/`, {
        withCredentials: true
      });
      setStudyTasks(updated.data.tasks || []);
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to add study task.");
    }
  };

  // Complete study task
  const toggleStudyTask = async (task) => {
    try {
      await axios.put(
        `${API}/study/${task.task_id}`,
        { is_completed: !task.is_completed },
        { withCredentials: true }
      );

      setStudyTasks(old => old.map(item =>
        item.task_id === task.task_id
          ? { ...item, is_completed: !item.is_completed }
          : item
      ));

      setNotice("Task status updated.");
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to update task.");
    }
  };

  // Delete study task
  const deleteStudyTask = async (taskId) => {
    try {
      const response = await axios.delete(
        `${API}/study/${taskId}`,
        { withCredentials: true }
      );

      setStudyTasks(old => old.filter(task => task.task_id !== taskId));
      setNotice(response.data.message || "Study task deleted successfully!");
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to delete task.");
    }
  };

  // Add reminder
  const addReminder = async (e) => {
    e.preventDefault();

    if (!reminderTitle.trim() || !reminderDate || !reminderTime) {
      setNotice("Please fill in the reminder title, date and time.");
      return;
    }

    try {
      const response = await axios.post(
        `${API}/reminders/`,
        {
          title: reminderTitle.trim(),
          description: reminderDescription.trim(),
          reminder_datetime: `${reminderDate} ${reminderTime}:00`
        },
        { withCredentials: true }
      );

      setReminderTitle("");
      setReminderDescription("");
      setReminderDate("");
      setReminderTime("");

      setNotice(response.data.message || "Reminder added successfully!");

      const updated = await axios.get(`${API}/reminders/`, {
        withCredentials: true
      });
      setReminders(updated.data.reminders || []);
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to add reminder.");
    }
  };

  // Complete reminder
  const toggleReminder = async (reminder) => {
    try {
      await axios.put(
        `${API}/reminders/${reminder.reminder_id}`,
        { is_completed: !reminder.is_completed },
        { withCredentials: true }
      );

      setReminders(old => old.map(item =>
        item.reminder_id === reminder.reminder_id
          ? { ...item, is_completed: !item.is_completed }
          : item
      ));

      setNotice("Reminder updated successfully!");
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to update reminder.");
    }
  };

  // Delete reminder
  const deleteReminder = async (reminderId) => {
    try {
      const response = await axios.delete(
        `${API}/reminders/${reminderId}`,
        { withCredentials: true }
      );

      setReminders(old => old.filter(item => item.reminder_id !== reminderId));
      setNotice(response.data.message || "Reminder deleted successfully!");
    } catch (error) {
      setNotice(error.response?.data?.message || "Unable to delete reminder.");
    }
  };

  if (!authChecked) {
    return <div className="auth-loading">Loading Serenify...</div>;
  }

// Show loading while checking the session
if (!authChecked) {
  return <div className="auth-loading">Loading Serenify...</div>;
}

// Admin dashboard
if (admin) {
  return (
    <AdminDashboard
      admin={admin}
      onLogout={() => {
        setAdmin(null);
        setUser(null);
        setAuthMode("student");
      }}
    />
  );
}

// Admin login
if (!user && authMode === "admin") {
  return (
    <AdminLogin
      onLogin={(adminData) => {
        setAdmin(adminData);
        setAuthMode("student");
      }}
    />
  );
}

// Student login
if (!user) {
  return (
    <Auth
      onLogin={setUser}
      onAdminLoginClick={() => setAuthMode("admin")}
    />
  );
}

  return (
    <div className="app-shell">

      {menuOpen && (
        <div
          className="mobile-overlay"
          onClick={() => setMenuOpen(false)}
        />
      )}

      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>

        <div className="brand">
          <div className="brand-icon">
            <Heart size={23} fill="white" />
          </div>
          <div>
            <h2>Serenify</h2>
            <span>Student wellbeing</span>
          </div>
          <button className="close-menu" onClick={() => setMenuOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <div className="side-label">MENU</div>

        <nav className="nav-list">
          {navigation.map(item => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${active === item.name ? "active" : ""}`}
                onClick={() => {
                  setActive(item.name);
                  setNotice("");
                  setMenuOpen(false);
                }}
              >
                <Icon size={19} />
                <span>{item.name}</span>
                {item.name === "Peer Support" && <span className="nav-dot" />}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">

          
        

          <div className="profile">
            <div className="avatar">S</div>
            <div className="profile-info">
              <strong>{user.full_name}</strong>
              <span>My personal space</span>
            </div>
            <button className="logout-button" onClick={handleLogout}>
              Logout
            </button>
          </div>

        </div>
      </aside>

      <main className="main-content">

        <header className="topbar">
          <div className="top-left">
            <button className="menu-button" onClick={() => setMenuOpen(true)}>
              <Menu size={22} />
            </button>
            <div className="breadcrumb">
              Workspace <ChevronRight size={14} />
              <strong>{active}</strong>
            </div>
          </div>

          <div className="top-actions">
            <div className="search-box">
              <Search size={17} />
              <input placeholder="Search anything..." />
              <span>⌘ K</span>
            </div>

            <button
              className="icon-button notification-button"
              onClick={() => setNotice("You are all caught up with your notifications.")}
            >
              <Bell size={19} /><i />
            </button>

            <div className="top-avatar">S</div>
          </div>
        </header>

        {/* DASHBOARD */}
        {active === "Dashboard" ? (

          <div className="dashboard">

            <section className="welcome-section">
              <div>
                <div className="date-label">
                  <Sun size={15} /> YOUR PERSONAL WELLNESS SPACE
                </div>
                <h1>A little progress, <span>every day.</span></h1>
                <p>Take a breath. You're doing better than you think. Let's make today count.</p>
              </div>

              <div className="welcome-art">
                <div className="sun-circle"><Sun size={42} /></div>
                <div className="art-leaf">✿</div>
                <div className="art-message">Breathe in.<br />Breathe out. ♡</div>
              </div>
            </section>

            <section className="stats-grid">

              <div className="stat-card">
                <div className="stat-top">
                  <span>Study progress</span>
                  <div className="stat-icon purple"><BookOpen size={19} /></div>
                </div>
                <h2>{completed}/{tasks.length} <small>tasks done</small></h2>
                <div className="progress-track">
                  <div style={{
                    width: `${tasks.length ? completed / tasks.length * 100 : 0}%`
                  }} />
                </div>
                <span className="stat-foot">Keep going, you're making progress!</span>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>Wellness streak</span>
                  <div className="stat-icon orange"><Flame size={19} /></div>
                </div>
                <h2>5 <small>days</small></h2>
                <span className="stat-foot">Small habits create big changes.</span>
                <div className="streak-dots">● ● ● ● ● <span>○ ○</span></div>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>Study tasks completed</span>
                  <div className="stat-icon blue"><Clock size={19} /></div>
                </div>
                <h2>{studyCompleted} <small>completed</small></h2>
                <span className="stat-foot">Open Study Planner to manage your tasks.</span>
              </div>

            </section>

            <div className="content-grid">

              <div className="left-column">

                <section className="panel mood-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">DAILY CHECK-IN</span>
                      <h2>How are you feeling today?</h2>
                      <p>There is no right or wrong answer. Just be you.</p>
                    </div>
                    <div className="heading-icon"><Heart size={22} /></div>
                  </div>

                  <div className="mood-options">
                    {[
                      ["Amazing", "😄"],
                      ["Good", "🙂"],
                      ["Okay", "😐"],
                      ["Stressed", "😟"],
                      ["Low", "😔"]
                    ].map(([label, emoji]) => (
                      <button
                        key={label}
                        className={`mood-option ${mood === label ? "selected" : ""}`}
                        onClick={() => selectMood(label)}
                      >
                        <span>{emoji}</span>
                        <small>{label}</small>
                      </button>
                    ))}
                  </div>

                  {notice && (
                    <div className="notice">
                      <CheckCircle2 size={15} /> {notice}
                    </div>
                  )}

                  <div className="mood-bottom">
                    <span><ShieldCheck size={15} /> Your check-in is private.</span>
                    <button onClick={() => setActive("Mood Tracker")}>
                      View mood history <ArrowUpRight size={15} />
                    </button>
                  </div>
                </section>

                <section className="panel chart-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">YOUR WELLBEING</span>
                      <h2>Mood overview</h2>
                      <p>A gentle look at your weekly check-ins.</p>
                    </div>
                    <span className="week-badge">This week <ChevronRight size={14} /></span>
                  </div>

                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={moodData}>
                        <defs>
                          <linearGradient id="moodGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#9B8BEA" stopOpacity={0.25} />
                            <stop offset="100%" stopColor="#9B8BEA" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis
                          dataKey="day"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#9995AC", fontSize: 12 }}
                        />
                        <Tooltip />
                        <Area
                          type="monotone"
                          dataKey="mood"
                          stroke="#9585DF"
                          strokeWidth={3}
                          fill="url(#moodGradient)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="chart-caption">
                    <span>♡ Your wellbeing journey is unique. Take it one day at a time.</span>
                  </div>
                </section>

                <section className="panel task-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">STAY ON TRACK</span>
                      <h2>Today's study plan</h2>
                      <p>One step at a time. You've got this!</p>
                    </div>
                    <button className="text-link" onClick={() => setActive("Study Planner")}>
                      View all <ArrowUpRight size={15} />
                    </button>
                  </div>

                  <div className="task-list">
                    {tasks.map(task => (
                      <div
                        className={`task-row ${task.done ? "task-done" : ""}`}
                        key={task.id}
                      >
                        <button className="task-check" onClick={() => toggleTask(task.id)}>
                          {task.done && <CheckCircle2 size={18} />}
                        </button>
                        <span className="task-title">{task.title}</span>
                        <span className="task-time">
                          <Clock size={13} /> {task.time}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>

              </div>

              <div className="right-column">

                <section className="ai-card">
                  <div className="ai-sparkle"><Sparkles size={21} /></div>
                  <span className="ai-label">YOUR SMART COMPANION</span>
                  <h2>A little help goes a long way.</h2>
                  <p>Need help organising your studies? Let's create a balanced plan that works for you.</p>
                  <button onClick={() => setActive("AI Assistant")}>
                    Talk to your AI companion <ArrowUpRight size={16} />
                  </button>
                  <div className="ai-decoration">✧</div>
                </section>

                <section className="panel reminder-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">TAKE CARE OF YOU</span>
                      <h2>Wellness reminders</h2>
                    </div>
                    <Bell size={19} className="muted-icon" />
                  </div>

                  <div className="reminder-item">
                    <div className="reminder-icon water"><Droplets size={19} /></div>
                    <div><strong>Drink some water</strong><span>Stay hydrated</span></div>
                    <span className="reminder-time">Now</span>
                  </div>

                  <div className="reminder-item">
                    <div className="reminder-icon break"><Coffee size={19} /></div>
                    <div><strong>Take a little break</strong><span>Give your mind a rest</span></div>
                    <span className="reminder-time">2:30 PM</span>
                  </div>

                  <div className="reminder-item">
                    <div className="reminder-icon sleep"><Moon size={19} /></div>
                    <div><strong>Wind down early</strong><span>Make time for sleep</span></div>
                    <span className="reminder-time">9:30 PM</span>
                  </div>

                  <button className="full-link" onClick={() => setActive("Reminders")}>
                    Manage reminders <ArrowUpRight size={15} />
                  </button>
                </section>

                <section className="support-card">
                  <div className="support-icon"><MessageCircle size={21} /></div>
                  <div>
                    <span>YOU ARE NOT ALONE</span>
                    <h3>Need someone to talk to?</h3>
                    <p>Support is always a strength, never a weakness.</p>
                  </div>
                  <button onClick={() => setActive("Counselling")}>
                    Find support <ChevronRight size={17} />
                  </button>
                </section>

                <div className="quote-card">
                  <span>✦ A GENTLE REMINDER</span>
                  <p>"You don't have to have it all figured out to move forward."</p>
                  <small>Be kind to yourself today ♡</small>
                </div>

              </div>
            </div>

            <footer className="footer">
              <span>♡ Serenify – Student Wellbeing Companion</span>
              <span>Made with care for your wellbeing.</span>
            </footer>

          </div>

        ) : active === "Mood Tracker" ? (

          // MOOD TRACKER
          <section className="placeholder-page mood-history-page">
            <div className="placeholder-icon"><Heart size={32} /></div>
            <span className="eyebrow">YOUR WELLBEING JOURNEY</span>
            <h1>Mood History</h1>
            <p>Every feeling matters. Take a look at your previous check-ins.</p>

            {moodLoading ? (
              <p>Loading your mood history...</p>
            ) : moodHistory.length === 0 ? (
              <p>You haven't recorded any moods yet.</p>
            ) : (
              <div className="mood-history-list">
                {moodHistory.map(item => (
                  <div className="mood-history-item" key={item.mood_id}>
                    <span className="history-emoji">
                      {moodEmojis[item.mood] || "💚"}
                    </span>
                    <div className="history-details">
                      <strong>{item.mood}</strong>
                      <span>{item.checkin_date}</span>
                    </div>
                    <span className="history-time">
                      {item.created_at
                        ? new Date(item.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit"
                          })
                        : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <button onClick={() => setActive("Dashboard")}>
              Back to dashboard <ArrowUpRight size={16} />
            </button>
          </section>

        ) : active === "Study Planner" ? (

          // STUDY PLANNER
          <section className="study-planner-page">

            <div className="study-planner-header">
              <div className="study-planner-icon"><BookOpen size={32} /></div>
              <span className="eyebrow">PLAN YOUR PROGRESS</span>
              <h1>Study Planner</h1>
              <p>Organise your study sessions, keep track of tasks, and celebrate each completed step.</p>
            </div>

            <div className="study-stats">
              <div className="study-stat-card">
                <span>Total Tasks</span>
                <h2>{studyTasks.length}</h2>
              </div>
              <div className="study-stat-card">
                <span>Completed</span>
                <h2>{studyCompleted}</h2>
              </div>
              <div className="study-stat-card">
                <span>Remaining</span>
                <h2>{studyRemaining}</h2>
              </div>
            </div>

            <div className="study-form-card">
              <h2>+ Add a study task</h2>
              <form onSubmit={addStudyTask}>
                <input
                  type="text"
                  placeholder="What do you need to study?"
                  value={newTaskTitle}
                  onChange={e => setNewTaskTitle(e.target.value)}
                  required
                />

                <div className="study-input-row">
                  <div>
                    <label>Study date</label>
                    <input
                      type="date"
                      value={newTaskDate}
                      onChange={e => setNewTaskDate(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label>Study time</label>
                    <input
                      type="time"
                      value={newTaskTime}
                      onChange={e => setNewTaskTime(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <button type="submit" className="add-study-button">
                  + Add task
                </button>
              </form>
            </div>

            <div className="study-task-section">
              <h2>Your study tasks</h2>

              {studyLoading ? (
                <p>Loading your tasks...</p>
              ) : studyTasks.length === 0 ? (
                <p className="empty-study-message">
                  No study tasks yet. Add your first task above.
                </p>
              ) : (
                <div className="study-task-list">
                  {studyTasks.map(task => (
                    <div
                      className={`study-task-item ${task.is_completed ? "completed-study-task" : ""}`}
                      key={task.task_id}
                    >
                      <input
                        type="checkbox"
                        checked={Boolean(task.is_completed)}
                        onChange={() => toggleStudyTask(task)}
                      />
                      <div className="study-task-details">
                        <strong>{task.title}</strong>
                        <span>
                          <CalendarDays size={14} /> {task.task_date}
                          &nbsp; · &nbsp;
                          <Clock size={14} /> {task.task_time}
                        </span>
                      </div>
                      <button
                        className="delete-study-button"
                        type="button"
                        onClick={() => deleteStudyTask(task.task_id)}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {notice && (
              <div className="study-notice">
                <CheckCircle2 size={16} /> {notice}
              </div>
            )}

            <button
              className="back-dashboard-button"
              onClick={() => {
                setNotice("");
                setActive("Dashboard");
              }}
            >
              Back to dashboard <ArrowUpRight size={16} />
            </button>

          </section>

        ) : active === "Reminders" ? (

          // REMINDERS
          <section className="study-planner-page reminders-page">

            <div className="study-planner-header">
              <div className="study-planner-icon"><Bell size={32} /></div>
              <span className="eyebrow">STAY ORGANIZED</span>
              <h1>Reminders</h1>
              <p>Keep track of important moments, deadlines and little things to do.</p>
            </div>

            <div className="study-stats">
              <div className="study-stat-card">
                <span>Total reminders</span>
                <h2>{reminders.length}</h2>
              </div>
              <div className="study-stat-card">
                <span>Completed</span>
                <h2>{reminders.filter(item => Boolean(item.is_completed)).length}</h2>
              </div>
              <div className="study-stat-card">
                <span>Upcoming</span>
                <h2>{reminders.filter(item => !item.is_completed).length}</h2>
              </div>
            </div>

            <div className="study-form-card">
              <h2>+ Create a reminder</h2>

              <form onSubmit={addReminder}>
                <input
                  type="text"
                  placeholder="Reminder title"
                  value={reminderTitle}
                  onChange={e => setReminderTitle(e.target.value)}
                  maxLength={255}
                  required
                />

                <textarea
                  placeholder="Description (optional)"
                  value={reminderDescription}
                  onChange={e => setReminderDescription(e.target.value)}
                  rows={3}
                />

                <div className="study-input-row">
                  <div>
                    <label>Reminder date</label>
                    <input
                      type="date"
                      value={reminderDate}
                      onChange={e => setReminderDate(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label>Reminder time</label>
                    <input
                      type="time"
                      value={reminderTime}
                      onChange={e => setReminderTime(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <button type="submit" className="add-study-button">
                  + Save reminder
                </button>
              </form>
            </div>

            <div className="study-task-section">
              <h2>Your reminders</h2>

              {reminderLoading ? (
                <p>Loading your reminders...</p>
              ) : reminders.length === 0 ? (
                <p className="empty-study-message">
                  No reminders yet. Create your first reminder above.
                </p>
              ) : (
                <div className="study-task-list">
                  {reminders.map(reminder => (
                    <div
                      className={`study-task-item ${reminder.is_completed ? "completed-study-task" : ""}`}
                      key={reminder.reminder_id}
                    >
                      <input
                        type="checkbox"
                        checked={Boolean(reminder.is_completed)}
                        onChange={() => toggleReminder(reminder)}
                      />

                      <div className="study-task-details">
                        <strong>{reminder.title}</strong>
                        {reminder.description && <small>{reminder.description}</small>}
                        <span>
                          <CalendarDays size={14} />
                          {new Date(reminder.reminder_datetime).toLocaleDateString()}
                          &nbsp; · &nbsp;
                          <Clock size={14} />
                          {new Date(reminder.reminder_datetime).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit"
                          })}
                        </span>
                      </div>

                      <button
                        className="delete-study-button"
                        type="button"
                        onClick={() => deleteReminder(reminder.reminder_id)}
                      >
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {notice && (
              <div className="study-notice">
                <CheckCircle2 size={16} /> {notice}
              </div>
            )}

            <button
              className="back-dashboard-button"
              onClick={() => {
                setNotice("");
                setActive("Dashboard");
              }}
            >
              Back to dashboard <ArrowUpRight size={16} />
            </button>

          </section>

        ) : active === "AI Assistant" ? (

          // AI ASSISTANT
          <AIAssistant />

        ) : active === "Peer Support" ? (
        
  <PeerSupport />
) : active === "Counselling" ? (
  <Counselling />

) : active === "Notifications" ? (

  <Notifications />
        ) : (

          // PLACEHOLDER FOR MODULES NOT DEVELOPED YET
          <section className="placeholder-page">
            <h1>{active}</h1>
            <p>This section is coming soon.</p>
            <button onClick={() => setActive("Dashboard")}>
              Back to dashboard <ArrowUpRight size={16} />
            </button>
          </section>

        )}

      </main>
    </div>
  );
}

export default App;
