import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  LifeBuoy,
  MessageCircleHeart,
  Send,
  Trash2,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
} from 'lucide-react';
import type { ChatMessage, PageId } from '../types';
import { apiFetch } from '../api';

interface CompanionPageProps {
  onNavigate: (page: PageId) => void;
}

const STARTER_PROMPTS = [
  'I feel overwhelmed by upcoming deadlines and do not know where to start.',
  'I have been feeling lonely on campus lately.',
  'How can I stop procrastinating when I feel anxious about grades?',
  'Suggest a 5-minute reset routine after a long study block.',
];

export function CompanionPage({ onNavigate }: CompanionPageProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [crisisVisible, setCrisisVisible] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const [voiceState, setVoiceState] = useState<'idle' | 'listening' | 'speaking'>('idle');
  const [voiceError, setVoiceError] = useState('');
  const [autoSpeak, setAutoSpeak] = useState(true);

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    setVoiceState('idle');
  };

  const speakReply = (text: string) => {
    if (!('speechSynthesis' in window)) {
      setVoiceError('Text-to-speech is not supported in this browser.');
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onstart = () => setVoiceState('speaking');
    utterance.onend = () => setVoiceState('idle');
    utterance.onerror = () => setVoiceState('idle');
    window.speechSynthesis.speak(utterance);
  };

  const startVoiceInput = () => {
    setVoiceError('');
    const SpeechRecognitionCtor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceError('Speech recognition is not available in this browser. Try Chrome or use text chat.');
      return;
    }
    try {
      const recognition = new SpeechRecognitionCtor();
      recognition.lang = navigator.language || 'en-IN';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => setVoiceState('listening');
      recognition.onresult = (event: any) => {
        const transcript = event.results?.[0]?.[0]?.transcript?.trim();
        if (transcript) {
          setInput(transcript);
          setVoiceState('idle');
          void sendMessage(transcript);
        }
      };
      recognition.onerror = (event: any) => {
        setVoiceState('idle');
        setVoiceError(event.error === 'not-allowed'
          ? 'Microphone permission was denied. Allow microphone access or type your message.'
          : 'Could not recognise speech. Try a quieter place or type your message.');
      };
      recognition.onend = () => setVoiceState((current) => current === 'listening' ? 'idle' : current);
      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setVoiceState('idle');
      setVoiceError('Unable to start the microphone. Please try again or type your message.');
    }
  };

  useEffect(() => () => {
    recognitionRef.current?.stop?.();
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  }, []);

  const loadChat = async () => {
    try {
      const res = await apiFetch<{ messages: ChatMessage[] }>('/api/chat');
      setMessages(res.messages);
      if (res.messages.some((m) => m.crisis_flagged === 1)) {
        setCrisisVisible(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load messages.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChat();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const sendMessage = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || sending) return;
    setError('');
    setSending(true);
    setInput('');

    const optimisticId = Date.now();
    const optimisticUser: ChatMessage = {
      id: optimisticId,
      role: 'user',
      content: trimmed,
      crisis_flagged: 0,
      source: 'user',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const res = await apiFetch<{
        userMessage: ChatMessage;
        assistantMessage: ChatMessage;
        crisisFlagged: boolean;
      }>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message: trimmed }),
      });

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticId),
        res.userMessage,
        res.assistantMessage,
      ]);
      if (res.crisisFlagged) {
        setCrisisVisible(true);
      }
      if (autoSpeak) speakReply(res.assistantMessage.content);
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      setInput(trimmed);
      setError(err instanceof Error ? err.message : 'Could not send message.');
    } finally {
      setSending(false);
    }
  };

  const handleClearChat = async () => {
    try {
      await apiFetch('/api/chat', { method: 'DELETE' });
      setMessages([]);
      setCrisisVisible(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to clear chat.');
    }
  };

  return (
    <div className="space-y-4">
      {/* Safety & Non-Diagnostic Notice */}
      <div className="bg-[#F3F0FF]/70 border border-[#DDD6FE] rounded-2xl px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-xs sm:text-sm text-slate-700">
          MindMate offers supportive reflection and study coping ideas. It does not diagnose conditions or replace licensed care.
        </p>
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={handleClearChat}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-rose-700"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Chat</span>
          </button>
          <button
            type="button"
            onClick={() => onNavigate('support')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-800 hover:underline"
          >
            <LifeBuoy className="w-3.5 h-3.5" />
            <span>Human Support</span>
          </button>
        </div>
      </div>

      {/* Prominent Emergency Banner if triggered */}
      {crisisVisible && (
        <div className="bg-rose-50 border border-rose-300 rounded-2xl p-5 space-y-3" role="alert">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-700 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h2 className="font-display text-base font-semibold text-rose-900">
                Immediate Support Is Available Right Now
              </h2>
              <p className="text-sm text-rose-800">
                If you are in immediate danger or feeling unable to stay safe, please call local emergency services (911 / 112), call or text 988 (US/Canada), or reach out to a trusted person nearby.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 pl-8">
            <button
              type="button"
              onClick={() => onNavigate('support')}
              className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-rose-700 hover:bg-rose-800 transition-colors"
            >
              Open Helplines & Campus Counsellors
            </button>
          </div>
        </div>
      )}

      {/* Chat Container */}
      <div className="bg-white rounded-2xl border border-slate-200/80 flex flex-col h-[560px]">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <p className="text-sm text-slate-500">Loading conversation...</p>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-[#EDE9FE] text-[#5B4FE9] flex items-center justify-center">
                <MessageCircleHeart className="w-6 h-6" />
              </div>
              <h3 className="font-display text-lg font-semibold text-slate-900">
                Start a quiet conversation
              </h3>
              <p className="text-sm text-slate-600">
                Share what&apos;s weighing on you—academic pressure, motivation dips, or needing a quick breather.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-[#5B4FE9] text-white'
                      : 'bg-slate-50 border border-slate-200/80 text-slate-800'
                  }`}
                >
                  <p>{msg.content}</p>
                  <p
                    className={`text-[11px] mt-1.5 ${
                      msg.role === 'user' ? 'text-indigo-100' : 'text-slate-400'
                    }`}
                  >
                    {msg.role === 'user' ? 'You' : 'MindMate Companion'} ·{' '}
                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))
          )}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl px-4 py-3 text-sm text-slate-500">
                Thinking carefully...
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Starter Prompts */}
        <div className="px-4 py-2.5 border-t border-slate-100 bg-slate-50/70 flex items-center gap-2 overflow-x-auto">
          {STARTER_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => sendMessage(prompt)}
              disabled={sending}
              className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs text-slate-700 hover:border-[#5B4FE9] hover:text-[#5B4FE9] transition-colors whitespace-nowrap shrink-0"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Voice Assistant Controls */}
        <div className="px-4 py-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
          <button type="button" onClick={startVoiceInput} disabled={sending || voiceState === 'listening'} className="inline-flex items-center gap-2 rounded-lg bg-[#F3F0FF] border border-[#DDD6FE] px-3 py-2 text-xs font-semibold text-indigo-800 disabled:opacity-50">
            <Mic className="w-4 h-4" /> {voiceState === 'listening' ? 'Listening…' : 'Speak to MindMate'}
          </button>
          {voiceState === 'listening' && <button type="button" onClick={() => { recognitionRef.current?.stop?.(); setVoiceState('idle'); }} className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-xs"><MicOff className="w-4 h-4" /> Stop listening</button>}
          <button type="button" onClick={() => setAutoSpeak((v) => !v)} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs text-slate-700">
            {autoSpeak ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />} {autoSpeak ? 'Voice replies on' : 'Voice replies off'}
          </button>
          {voiceState === 'speaking' && <button type="button" onClick={stopSpeaking} className="rounded-lg bg-rose-50 border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700">Stop speaking</button>}
          {voiceState === 'listening' && <span className="text-xs text-indigo-700" role="status">Microphone is listening…</span>}
          {voiceState === 'speaking' && <span className="text-xs text-teal-700" role="status">MindMate is speaking…</span>}
          {voiceError && <p className="w-full text-xs text-rose-700" role="alert">{voiceError}</p>}
          <p className="w-full text-[11px] text-slate-500">Voice recognition uses your browser's speech service; availability and processing vary by browser. You can always use text chat instead.</p>
        </div>

        {/* Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="p-4 border-t border-slate-200/80 flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Share how your studies or day are feeling..."
            aria-label="Message AI Wellbeing Companion"
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors disabled:opacity-50 whitespace-nowrap shrink-0"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </form>
      </div>

      {error && (
        <p className="text-sm text-rose-700" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
