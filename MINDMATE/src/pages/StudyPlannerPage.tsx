import React, { useEffect, useState } from 'react';
import {
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  Pencil,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import type { StudyTask } from '../types';
import { apiFetch } from '../api';

const TIME_SLOTS = [
  'Morning (09:00 - 11:00)',
  'Midday (11:30 - 13:00)',
  'Afternoon (14:00 - 16:00)',
  'Evening (18:30 - 20:00)',
  'Night Wind-Down (20:30 - 21:30)',
];

export function StudyPlannerPage() {
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('all');
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [subject, setSubject] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [deadline, setDeadline] = useState(new Date().toISOString().slice(0, 10));
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium');
  const [scheduledSlot, setScheduledSlot] = useState(TIME_SLOTS[0]);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  const loadTasks = async () => {
    try {
      const res = await apiFetch<{ tasks: StudyTask[] }>('/api/tasks');
      setTasks(res.tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load study tasks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const resetForm = () => {
    setEditingId(null);
    setSubject('');
    setTitle('');
    setDescription('');
    setDeadline(new Date().toISOString().slice(0, 10));
    setPriority('medium');
    setScheduledSlot(TIME_SLOTS[0]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    try {
      if (editingId) {
        await apiFetch(`/api/tasks/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify({
            subject,
            title,
            description,
            deadline,
            priority,
            scheduled_slot: scheduledSlot,
          }),
        });
        setFeedback('Study task updated.');
      } else {
        await apiFetch('/api/tasks', {
          method: 'POST',
          body: JSON.stringify({
            subject,
            title,
            description,
            deadline,
            priority,
            scheduled_slot: scheduledSlot,
          }),
        });
        setFeedback('New study task added to your schedule.');
      }
      resetForm();
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save task.');
    }
  };

  const handleEdit = (task: StudyTask) => {
    setEditingId(task.id);
    setSubject(task.subject);
    setTitle(task.title);
    setDescription(task.description);
    setDeadline(task.deadline);
    setPriority(task.priority);
    setScheduledSlot(task.scheduled_slot || TIME_SLOTS[0]);
  };

  const handleToggle = async (task: StudyTask) => {
    try {
      const res = await apiFetch<{ task: StudyTask }>(`/api/tasks/${task.id}`, {
        method: 'PUT',
        body: JSON.stringify({ completed: !task.completed }),
      });
      setTasks((prev) => prev.map((t) => (t.id === task.id ? res.task : t)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update task.');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiFetch(`/api/tasks/${id}`, { method: 'DELETE' });
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete task.');
    }
  };

  const filteredTasks = tasks.filter((t) => {
    if (filter === 'pending') return !t.completed;
    if (filter === 'completed') return Boolean(t.completed);
    return true;
  });

  const pendingCount = tasks.filter((t) => !t.completed).length;
  const completedCount = tasks.filter((t) => Boolean(t.completed)).length;

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Add / Edit Form */}
        <form
          onSubmit={handleSubmit}
          className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4 h-fit"
        >
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-slate-900">
              {editingId ? 'Edit Study Task' : 'Add Study Task'}
            </h2>
            {editingId && (
              <button
                type="button"
                onClick={resetForm}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900"
              >
                <X className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="task-subject">
              Subject / Course
            </label>
            <input
              id="task-subject"
              type="text"
              required
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g., Operating Systems"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="task-title">
              Task Title
            </label>
            <input
              id="task-title"
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Summarize scheduling algorithms"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="task-desc">
              Notes / Sub-steps
            </label>
            <textarea
              id="task-desc"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Keep the step small and actionable..."
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="task-deadline">
                Deadline
              </label>
              <input
                id="task-deadline"
                type="date"
                required
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="task-priority">
                Priority
              </label>
              <select
                id="task-priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high')}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="task-slot">
              Daily Study Slot
            </label>
            <select
              id="task-slot"
              value={scheduledSlot}
              onChange={(e) => setScheduledSlot(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            >
              {TIME_SLOTS.map((slot) => (
                <option key={slot} value={slot}>
                  {slot}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-rose-700">{error}</p>}
          {feedback && <p className="text-sm text-teal-700">{feedback}</p>}

          <button
            type="submit"
            className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors inline-flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span>{editingId ? 'Update Task' : 'Add to Study Plan'}</span>
          </button>
        </form>

        {/* Task List */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-display text-lg font-semibold text-slate-900">Your Study Tasks</h3>
              <p className="text-xs text-slate-500">
                {pendingCount} pending · {completedCount} completed
              </p>
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl">
              {(['all', 'pending', 'completed'] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setFilter(tab)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                    filter === tab ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <p className="text-sm text-slate-500">Loading study tasks...</p>
          ) : filteredTasks.length === 0 ? (
            <div className="p-8 text-center rounded-xl bg-slate-50 border border-slate-200/70">
              <p className="text-sm font-medium text-slate-700">No tasks in this view</p>
              <p className="text-xs text-slate-500 mt-1">Use the form on the left to add a manageable study step.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredTasks.map((task) => (
                <div key={task.id} className="py-4 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <button
                      type="button"
                      onClick={() => handleToggle(task)}
                      className="mt-0.5 text-slate-400 hover:text-[#5B4FE9] shrink-0"
                      aria-label={`Toggle completion for ${task.title}`}
                    >
                      {task.completed ? (
                        <CheckCircle2 className="w-5 h-5 text-teal-600" />
                      ) : (
                        <Circle className="w-5 h-5" />
                      )}
                    </button>
                    <div className="min-w-0 space-y-1">
                      <p
                        className={`text-sm font-semibold ${
                          task.completed ? 'line-through text-slate-400' : 'text-slate-900'
                        }`}
                      >
                        {task.title}
                      </p>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span className="font-medium text-slate-700">{task.subject}</span>
                        <span aria-hidden="true">·</span>
                        <span
                          className={
                            task.priority === 'high'
                              ? 'text-rose-700 font-medium'
                              : task.priority === 'medium'
                              ? 'text-amber-700 font-medium'
                              : 'text-teal-700 font-medium'
                          }
                        >
                          {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)} priority
                        </span>
                        <span aria-hidden="true">·</span>
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {task.deadline}
                        </span>
                      </div>
                      {task.description && <p className="text-xs text-slate-600">{task.description}</p>}
                      <p className="text-xs text-[#5B4FE9] inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{task.scheduled_slot}</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => handleEdit(task)}
                      className="p-2 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100"
                      aria-label={`Edit ${task.title}`}
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(task.id)}
                      className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                      aria-label={`Delete ${task.title}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Daily Study Schedule View */}
      <section className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
        <div>
          <h3 className="font-display text-lg font-semibold text-slate-900">Daily Study Schedule</h3>
          <p className="text-xs text-slate-500">Balanced time blocks with built-in rest spacing</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {TIME_SLOTS.map((slot) => {
            const slotTasks = tasks.filter((t) => t.scheduled_slot === slot && !t.completed);
            return (
              <div key={slot} className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2">
                <p className="text-xs font-semibold text-slate-800">{slot}</p>
                {slotTasks.length === 0 ? (
                  <p className="text-xs text-slate-400">Open for rest or light review</p>
                ) : (
                  <ul className="space-y-1.5">
                    {slotTasks.map((t) => (
                      <li key={t.id} className="p-2 rounded-lg bg-white border border-slate-200/70 text-xs">
                        <p className="font-medium text-slate-900 truncate">{t.title}</p>
                        <p className="text-slate-500 truncate">{t.subject}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
