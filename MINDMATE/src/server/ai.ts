import { GoogleGenAI } from '@google/genai';

const CRISIS_PATTERNS = [
  /\b(kill myself|end my life|want to die|suicide|suicidal|hurt myself|self[- ]harm|cut myself|no reason to live|better off dead|overdose)\b/i,
];

export function detectCrisisLanguage(text: string): boolean {
  return CRISIS_PATTERNS.some((pattern) => pattern.test(text));
}

export interface CompanionReply {
  content: string;
  crisisFlagged: boolean;
  source: 'gemini' | 'fallback';
}

const SYSTEM_INSTRUCTION = `You are MindMate, a warm, empathetic, non-judgmental digital wellbeing companion for college and university students.
Guidelines:
1. Be compassionate, validating, concise (2-4 short paragraphs max), and practical.
2. Help students reflect on academic stress, exam anxiety, procrastination, loneliness, sleep, and study-life balance.
3. Suggest simple, concrete coping actions (e.g., 4-4-4 box breathing, breaking a task into a 15-minute starter step, taking a short screen break, journaling, or reaching out to a friend or campus counsellor).
4. NEVER diagnose medical or psychiatric conditions, prescribe medication, or claim to replace licensed mental health professionals.
5. Keep tone grounded, encouraging, and human—avoid cliché robotic hype.`;

const CRISIS_RESPONSE = `I'm really glad you reached out, and I want to make sure you are safe right now. What you're carrying sounds very heavy, and you don't have to face it alone.

Because I'm a digital companion and not a crisis professional, please reach out to someone who can support you right now:
• Call or text **988** (Suicide & Crisis Lifeline, US/Canada, free & 24/7) or **112 / 911** for immediate local emergency help.
• Text **HOME to 741741** to connect with the Crisis Text Line.
• Outside North America, visit **findahelpline.com** for free, confidential 24/7 support in your country, or contact your campus security / trusted friend or family member nearby.

I have also highlighted the Emergency Support card below so you can open campus and crisis resources anytime.`;

function generateEmpatheticFallback(userMessage: string, studentName: string, latestMood?: string): string {
  const msg = userMessage.toLowerCase();
  const name = studentName.split(' ')[0] || 'friend';

  if (/\b(exam|test|deadline|assignment|homework|study|grade|fail|overwhelm|thesis|project)\b/.test(msg)) {
    return `It makes complete sense to feel weighed down when academic deadlines stack up, ${name}. When everything feels urgent at once, our brains often freeze rather than prioritize.\n\nTry shrinking the horizon for just the next 25 minutes: pick **one** concrete micro-step (like outlining 3 bullet points or solving a single practice question) and start a Pomodoro timer in your Study Planner. You don't have to finish the whole mountain tonight—just take one steady step, then give yourself a real 5-minute break away from screens.`;
  }

  if (/\b(lonely|alone|isolated|friends|homesick|miss home|left out)\b/.test(msg)) {
    return `Feeling disconnected on campus can be surprisingly painful, ${name}, especially when it looks like everyone else already has their routine figured out. You're definitely not the only student feeling that way.\n\nA gentle low-pressure step today could be studying in a shared library space for an hour, sending a short check-in text to someone from home, or reading a few stories in the Peer Support Community here so you remember you're in good company. Would you like to brainstorm one small, low-pressure way to connect this week?`;
  }

  if (/\b(sleep|tired|exhausted|burnout|burnt out|fatigue|insomnia|drain)\b/.test(msg)) {
    return `Running on empty makes every assignment feel twice as hard, ${name}. Your body asking for rest isn't laziness—it's a signal that your cognitive battery genuinely needs recovery.\n\nIf you can, protect a 20-minute screen-free wind-down before bed tonight, and try the 3-minute guided breathing reset in the Stress Relief Toolkit right now to release shoulder and jaw tension. Let's also keep tomorrow's study schedule realistic with just 1–2 priority blocks.`;
  }

  if (/\b(anxious|anxiety|panic|worried|nervous|scared|stress|stressed)\b/.test(msg)) {
    return `I hear how tense things feel right now, ${name}. Anxiety often pulls our attention into worst-case futures, which can feel exhausting in the moment.\n\nLet's bring things back to the present 60 seconds: drop your shoulders, unclench your jaw, and try three slow rounds of Box Breathing (inhale 4s, hold 4s, exhale 4s, rest 4s). Once your nervous system settles a notch, write down the single thing bothering you most—we can break it into one manageable step together.`;
  }

  if (/\b(motivat|procrastinat|stuck|lazy|focus|distract)\b/.test(msg)) {
    return `Getting started is almost always the hardest friction point, ${name}—and procrastination is usually emotional overwhelm in disguise, not a personal flaw.\n\nTry the "5-minute permission rule": tell yourself you only have to open the document and work on it for 5 minutes. If you still want to stop after 5 minutes, you have full permission to pause. Usually, crossing that starting line quietly dissolves half the dread.`;
  }

  const moodAck = latestMood
    ? `I noticed your recent check-in noted feeling **${latestMood.toLowerCase()}**—thank you for checking in with yourself.`
    : `Thank you for sharing what's on your mind today.`;

  return `${moodAck} Studying and managing daily life at university takes a lot of quiet emotional energy, ${name}.\n\nIf it helps right now, we can either organize your top two study priorities into calmer time blocks, walk through a quick breathing reset, or simply talk through whatever feels heaviest today. What would feel most supportive in the next 10 minutes?`;
}

export async function generateWellbeingReply(params: {
  userMessage: string;
  history: Array<{ role: string; content: string }>;
  studentName: string;
  latestMood?: string;
}): Promise<CompanionReply> {
  if (detectCrisisLanguage(params.userMessage)) {
    return {
      content: CRISIS_RESPONSE,
      crisisFlagged: true,
      source: 'fallback',
    };
  }

  const apiKey = process.env.GEMINI_API_KEY?.trim();
  const hasRealKey = Boolean(apiKey && apiKey !== 'MY_GEMINI_API_KEY');

  if (!hasRealKey) {
    return {
      content: generateEmpatheticFallback(params.userMessage, params.studentName, params.latestMood),
      crisisFlagged: false,
      source: 'fallback',
    };
  }

  try {
    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });

    const recentHistory = params.history
      .slice(-8)
      .map((m) => `${m.role === 'user' ? 'Student' : 'MindMate'}: ${m.content}`)
      .join('\n');

    const contextHeader = [
      `Student first name: ${params.studentName.split(' ')[0]}`,
      params.latestMood ? `Latest recorded mood: ${params.latestMood}` : '',
      recentHistory ? `Recent conversation:\n${recentHistory}` : '',
      `Student's new message: ${params.userMessage}`,
    ]
      .filter(Boolean)
      .join('\n\n');

    const response = await ai.models.generateContent({
      model: 'gemini-4-hydrogen',
      contents: contextHeader,
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
      },
    });

    const replyText = response.text?.trim();
    if (!replyText) {
      throw new Error('Empty response from Gemini');
    }

    return {
      content: replyText,
      crisisFlagged: false,
      source: 'gemini',
    };
  } catch (err) {
    console.warn('Gemini API unavailable, using empathetic fallback:', err instanceof Error ? err.message : err);
    return {
      content: generateEmpatheticFallback(params.userMessage, params.studentName, params.latestMood),
      crisisFlagged: false,
      source: 'fallback',
    };
  }
}
