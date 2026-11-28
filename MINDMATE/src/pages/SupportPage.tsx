import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Mail,
  MapPin,
  Phone,
  ShieldCheck,
} from 'lucide-react';
import type { Counsellor, CounsellorRequest } from '../types';
import { apiFetch } from '../api';

const HELPLINES = [
  {
    name: '988 Suicide & Crisis Lifeline',
    contact: 'Call or Text 988',
    availability: '24/7 · Free & Confidential (US & Canada)',
  },
  {
    name: 'Crisis Text Line',
    contact: 'Text HOME to 741741',
    availability: '24/7 · SMS Support with Trained Volunteers',
  },
  {
    name: 'Emergency Services',
    contact: 'Call 911 / 112 / 999',
    availability: 'Immediate Physical or Medical Emergency',
  },
  {
    name: 'International Helplines Directory',
    contact: 'findahelpline.com',
    availability: 'Verified Global Crisis Support by Country',
  },
];

export function SupportPage() {
  const [counsellors, setCounsellors] = useState<Counsellor[]>([]);
  const [requests, setRequests] = useState<CounsellorRequest[]>([]);
  const [selectedCounsellor, setSelectedCounsellor] = useState('');
  const [preferredSlot, setPreferredSlot] = useState('Tomorrow · 10:00 AM');
  const [topic, setTopic] = useState('');
  const [consentGiven, setConsentGiven] = useState(false);
  const [urgentMode, setUrgentMode] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  const loadSupport = async () => {
    try {
      const res = await apiFetch<{ counsellors: Counsellor[]; requests: CounsellorRequest[] }>(
        '/api/support/counsellors'
      );
      setCounsellors(res.counsellors);
      setRequests(res.requests);
      if (res.counsellors.length > 0 && !selectedCounsellor) {
        setSelectedCounsellor(res.counsellors[0].name);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadSupport();
  }, []);

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFeedback('');
    if (!consentGiven) {
      setError('Please check the explicit consent box before submitting your outreach request.');
      return;
    }
    try {
      await apiFetch('/api/support/request', {
        method: 'POST',
        body: JSON.stringify({
          counsellor_name: selectedCounsellor,
          preferred_slot: preferredSlot,
          topic,
          consent_given: consentGiven,
        }),
      });
      setTopic('');
      setConsentGiven(false);
      setFeedback('Your consent-verified support request has been recorded. Nothing was shared externally without your approval.');
      await loadSupport();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to submit support request.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Emergency Banner & Urgent Toggle */}
      <section className="bg-rose-50 border border-rose-200 rounded-2xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-rose-700 shrink-0 mt-0.5" />
            <div>
              <h2 className="font-display text-lg font-semibold text-rose-950">
                Immediate Safety & Crisis Support
              </h2>
              <p className="text-sm text-rose-900 mt-1">
                If you or someone near you is in immediate danger, please contact local emergency services (911 / 112), call 988, or reach out to a trusted person right away. MINDMATE never contacts anyone automatically without your permission.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setUrgentMode((v) => !v)}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-rose-700 hover:bg-rose-800 transition-colors whitespace-nowrap shrink-0"
          >
            {urgentMode ? 'Hide Urgent Steps' : 'I Need Urgent Help Now'}
          </button>
        </div>

        {urgentMode && (
          <div className="bg-white rounded-xl border border-rose-200 p-4 space-y-2 text-sm text-slate-800">
            <p className="font-semibold text-rose-900">Immediate Next Steps:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Call local emergency services (911 / 112) or go to the nearest hospital emergency department.</li>
              <li>Call or text <strong>988</strong> (24/7 Lifeline) or text <strong>HOME to 741741</strong>.</li>
              <li>Stay near a trusted roommate, friend, family member, or campus resident advisor.</li>
            </ol>
          </div>
        )}
      </section>

      {/* Trusted Helplines */}
      <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {HELPLINES.map((line) => (
          <div key={line.name} className="bg-white rounded-2xl border border-slate-200/80 p-5 space-y-1.5">
            <p className="font-display text-sm font-semibold text-slate-900">{line.name}</p>
            <p className="font-mono-tabular text-sm font-semibold text-[#5B4FE9]">{line.contact}</p>
            <p className="text-xs text-slate-500">{line.availability}</p>
          </div>
        ))}
      </section>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Campus Counsellors Directory (Configurable Sample Data) */}
        <section className="lg:col-span-7 space-y-4">
          <div>
            <h3 className="font-display text-lg font-semibold text-slate-900">
              Campus Counselling Directory
            </h3>
            <p className="text-xs text-slate-500">
              Sample campus wellness office contacts (configurable per institution)
            </p>
          </div>

          <div className="space-y-3">
            {counsellors.map((c) => (
              <div key={c.id} className="bg-white rounded-2xl border border-slate-200/80 p-5 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h4 className="font-display text-base font-semibold text-slate-900">{c.name}</h4>
                    <p className="text-xs text-[#5B4FE9] font-medium">{c.role}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedCounsellor(c.name)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#F3F0FF] text-[#4338CA] hover:bg-[#EDE9FE]"
                  >
                    Select for Request
                  </button>
                </div>
                <p className="text-xs text-slate-600">{c.focus}</p>
                <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-4 text-xs text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" /> {c.office}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Phone className="w-3.5 h-3.5" /> {c.phone}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5" /> {c.contactEmail}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Consent-First Outreach Request Form */}
        <section className="lg:col-span-5 space-y-4">
          <form
            onSubmit={handleRequestSubmit}
            className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4"
          >
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-teal-700" />
              <h3 className="font-display text-lg font-semibold text-slate-900">
                Request Human Support
              </h3>
            </div>
            <p className="text-xs text-slate-600">
              Schedule a confidential campus check-in only when you explicitly consent below.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="sup-counsellor">
                Preferred Counsellor
              </label>
              <select
                id="sup-counsellor"
                value={selectedCounsellor}
                onChange={(e) => setSelectedCounsellor(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
              >
                {counsellors.map((c) => (
                  <option key={c.id} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="sup-slot">
                Preferred Time Window
              </label>
              <select
                id="sup-slot"
                value={preferredSlot}
                onChange={(e) => setPreferredSlot(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
              >
                <option value="Tomorrow · 10:00 AM">Tomorrow · 10:00 AM</option>
                <option value="Tomorrow · 02:30 PM">Tomorrow · 02:30 PM</option>
                <option value="This Week · Morning">This Week · Morning</option>
                <option value="This Week · Afternoon">This Week · Afternoon</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="sup-topic">
                What would you like to discuss? (Optional)
              </label>
              <textarea
                id="sup-topic"
                rows={3}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., Exam stress, sleep routine, adjusting to final year..."
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
              />
            </div>

            <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={consentGiven}
                onChange={(e) => setConsentGiven(e.target.checked)}
                className="mt-0.5 rounded border-slate-300 accent-teal-700"
              />
              <span>
                I explicitly consent to recording this support appointment request. No personal mood logs or AI chats will be attached without my separate approval.
              </span>
            </label>

            {error && <p className="text-xs text-rose-700">{error}</p>}
            {feedback && (
              <p className="text-xs text-teal-800 bg-[#ECFDF5] p-3 rounded-xl border border-teal-200">
                {feedback}
              </p>
            )}

            <button
              type="submit"
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-teal-700 hover:bg-teal-800 transition-colors"
            >
              Submit Consent-Verified Request
            </button>
          </form>

          {requests.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200/80 p-5 space-y-3">
              <h4 className="font-display text-sm font-semibold text-slate-900">Your Support Requests</h4>
              <ul className="space-y-2 text-xs">
                {requests.map((r) => (
                  <li key={r.id} className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1">
                    <div className="flex items-center justify-between font-semibold text-slate-900">
                      <span>{r.counsellor_name}</span>
                      <span className="inline-flex items-center gap-1 text-teal-700">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Confirmed
                      </span>
                    </div>
                    <p className="text-slate-600">{r.preferred_slot} · {r.topic}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
