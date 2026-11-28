import React, { useEffect, useState } from 'react';
import { Bell, Check, Eye, Pause, Play, RefreshCw, Sparkles, Wind } from 'lucide-react';
import { motion } from 'motion/react';

const BREATH_PHASES = [
  { label: 'Inhale gently', duration: 4, scale: 1.25 },
  { label: 'Hold softly', duration: 4, scale: 1.25 },
  { label: 'Exhale slowly', duration: 4, scale: 0.9 },
  { label: 'Rest & release', duration: 4, scale: 0.9 },
];

const AFFIRMATIONS = [
  'My worth as a student is not defined by a single grade or deadline.',
  'Small, steady progress today is enough.',
  'Resting my mind is part of learning effectively, not a detour.',
  'I can take this semester one assignment and one breath at a time.',
  'Asking for help from peers or professors is a sign of wisdom.',
];

const MEDITATIONS = [
  {
    title: '3-Minute Pre-Exam Grounding',
    duration: '3 min',
    steps: [
      'Place both feet flat on the floor and rest your hands on your desk.',
      'Notice 3 neutral sounds in the room without judging them.',
      'Drop your shoulders away from your ears and soften your jaw.',
      'Take five unhurried exhales slightly longer than your inhales.',
    ],
  },
  {
    title: '5-Minute Desk Tension Reset',
    duration: '5 min',
    steps: [
      'Close your laptop lid or dim your screen for five minutes.',
      'Roll your shoulders slowly backward four times.',
      'Gently tilt your ear toward each shoulder for 15 seconds per side.',
      'Close your eyes and picture a calm outdoor place you enjoy.',
    ],
  },
];

const RELAXATION_IDEAS = [
  'Step outside for 10 minutes of natural daylight without headphones',
  'Drink a full glass of water and stretch your wrists',
  'Listen to one calm instrumental track with your eyes closed',
  'Tidy just the top of your study desk to lower visual clutter',
  'Send a quick voice note or text to a friend or family member',
];

export function ToolkitPage() {
  const [breathingActive, setBreathingActive] = useState(false);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [phaseSec, setPhaseSec] = useState(4);
  const [cycles, setCycles] = useState(0);

  const [affirmationIdx, setAffirmationIdx] = useState(0);
  const [checkedActivities, setCheckedActivities] = useState<Record<number, boolean>>({});
  const [screenBreakEnabled, setScreenBreakEnabled] = useState(true);
  const [screenBreakSeconds, setScreenBreakSeconds] = useState(20 * 60);
  const [screenAlert, setScreenAlert] = useState(false);
  const [imgError, setImgError] = useState(false);

  // Breathing timer
  useEffect(() => {
    if (!breathingActive) return;
    const id = window.setInterval(() => {
      setPhaseSec((prev) => {
        if (prev <= 1) {
          setPhaseIdx((curr) => {
            const next = (curr + 1) % BREATH_PHASES.length;
            if (next === 0) setCycles((c) => c + 1);
            return next;
          });
          return 4;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [breathingActive]);

  // 20-20-20 Screen-Break Reminder timer
  useEffect(() => {
    if (!screenBreakEnabled) return;
    const id = window.setInterval(() => {
      setScreenBreakSeconds((prev) => {
        if (prev <= 1) {
          setScreenAlert(true);
          return 20 * 60;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [screenBreakEnabled]);

  const currentPhase = BREATH_PHASES[phaseIdx];
  const breakMins = String(Math.floor(screenBreakSeconds / 60)).padStart(2, '0');
  const breakSecs = String(screenBreakSeconds % 60).padStart(2, '0');

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Guided Box Breathing */}
        <section className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 flex flex-col items-center text-center space-y-6">
          <div className="space-y-1">
            <h2 className="font-display text-xl font-semibold text-slate-900">
              4-4-4-4 Box Breathing
            </h2>
            <p className="text-sm text-slate-500">
              Slows heart rate and calms nervous tension before exams or sleep.
            </p>
          </div>

          <div className="relative w-56 h-56 flex items-center justify-center">
            <motion.div
              animate={{
                scale: breathingActive ? currentPhase.scale : 1,
              }}
              transition={{ duration: 1.8, ease: 'easeInOut' }}
              className="w-40 h-40 rounded-full bg-gradient-to-br from-[#EDE9FE] via-[#EFF6FF] to-[#D1FAE5] border border-[#C4B5FD] flex flex-col items-center justify-center shadow-xs"
            >
              <Wind className="w-6 h-6 text-[#5B4FE9] mb-1" />
              <p className="text-sm font-semibold text-slate-900">
                {breathingActive ? currentPhase.label : 'Ready'}
              </p>
              <p className="font-mono-tabular text-xs text-slate-600 mt-0.5">
                {breathingActive ? `${phaseSec}s` : '4s cycle'}
              </p>
            </motion.div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setBreathingActive((a) => !a)}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors"
            >
              {breathingActive ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{breathingActive ? 'Pause Breathing' : 'Start Guided Breathing'}</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setBreathingActive(false);
                setPhaseIdx(0);
                setPhaseSec(4);
              }}
              className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
            >
              Reset
            </button>
          </div>

          <p className="text-xs text-slate-500 font-mono-tabular">
            Completed breathing cycles this session: {cycles}
          </p>
        </section>

        {/* Mindfulness Stillness & Affirmations */}
        <div className="lg:col-span-6 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden grid sm:grid-cols-12">
            <div className="sm:col-span-5 min-h-[180px] bg-[#F3F0FF]">
              {!imgError ? (
                <img
                  src="/src/assets/images/toolkit_mindfulness_stillness_1795623793262.jpg"
                  alt="Smooth river stones, eucalyptus, lavender and warm tea on linen"
                  referrerPolicy="no-referrer"
                  onError={() => setImgError(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#F3F0FF] to-[#ECFDF5] p-6">
                  <Sparkles className="w-8 h-8 text-teal-700" />
                </div>
              )}
            </div>
            <div className="sm:col-span-7 p-6 flex flex-col justify-between space-y-4">
              <div>
                <p className="text-xs font-semibold text-teal-700">Positive Affirmation</p>
                <p className="font-display text-lg font-medium text-slate-900 mt-2 leading-snug">
                  &ldquo;{AFFIRMATIONS[affirmationIdx]}&rdquo;
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAffirmationIdx((i) => (i + 1) % AFFIRMATIONS.length)}
                className="inline-flex items-center gap-2 text-xs font-semibold text-[#5B4FE9] hover:underline self-start"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Next Affirmation</span>
              </button>
            </div>
          </div>

          {/* 20-20-20 Screen-Break Reminder */}
          <div className="bg-[#EFF6FF]/70 rounded-2xl border border-sky-200/80 p-6 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-white text-sky-700 border border-sky-200 flex items-center justify-center shrink-0">
                  <Eye className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-display text-base font-semibold text-slate-900">
                    20-20-20 Screen-Break Reminder
                  </h3>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Every 20 minutes, look 20 feet away for 20 seconds to ease eye strain.
                  </p>
                </div>
              </div>
              <span className="font-mono-tabular text-sm font-semibold text-sky-900 bg-white px-3 py-1 rounded-lg border border-sky-200">
                {breakMins}:{breakSecs}
              </span>
            </div>

            {screenAlert && (
              <div className="p-3 rounded-xl bg-white border border-sky-200 flex items-center justify-between gap-3 text-xs text-slate-800">
                <span className="inline-flex items-center gap-1.5 font-medium">
                  <Bell className="w-4 h-4 text-sky-700" />
                  Time for a 20-second eye & posture break! Look out a window or across the room.
                </span>
                <button
                  type="button"
                  onClick={() => setScreenAlert(false)}
                  className="font-semibold text-[#5B4FE9] hover:underline shrink-0"
                >
                  Dismiss
                </button>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => setScreenBreakEnabled((v) => !v)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-white border border-sky-200 text-sky-900 hover:bg-sky-50"
              >
                {screenBreakEnabled ? 'Pause Reminder' : 'Resume Reminder'}
              </button>
              <button
                type="button"
                onClick={() => setScreenAlert(true)}
                className="text-xs font-medium text-sky-800 hover:underline"
              >
                Preview Break Alert
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Guided Meditations & Relaxation Checklist */}
      <div className="grid lg:grid-cols-12 gap-6">
        <section className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
          <h3 className="font-display text-lg font-semibold text-slate-900">Short Guided Meditations</h3>
          <div className="grid sm:grid-cols-2 gap-4">
            {MEDITATIONS.map((med) => (
              <div key={med.title} className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2.5">
                <div className="flex items-center justify-between">
                  <h4 className="font-display text-sm font-semibold text-slate-900">{med.title}</h4>
                  <span className="text-xs font-mono-tabular text-[#5B4FE9]">{med.duration}</span>
                </div>
                <ol className="space-y-1.5 text-xs text-slate-600 list-decimal list-inside">
                  {med.steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </section>

        <section className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-3">
          <h3 className="font-display text-lg font-semibold text-slate-900">Quick Relaxation Activities</h3>
          <p className="text-xs text-slate-500">Pick one small offline reset after a study block</p>
          <ul className="space-y-2 pt-1">
            {RELAXATION_IDEAS.map((idea, idx) => {
              const done = Boolean(checkedActivities[idx]);
              return (
                <li key={idea}>
                  <button
                    type="button"
                    onClick={() => setCheckedActivities((prev) => ({ ...prev, [idx]: !prev[idx] }))}
                    className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left text-xs transition-colors ${
                      done
                        ? 'bg-[#ECFDF5] border-teal-200 text-teal-900'
                        : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <span
                      className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5 ${
                        done ? 'bg-teal-600 border-teal-600 text-white' : 'border-slate-300'
                      }`}
                    >
                      {done && <Check className="w-3 h-3" />}
                    </span>
                    <span className={done ? 'line-through opacity-80' : ''}>{idea}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </div>
  );
}
