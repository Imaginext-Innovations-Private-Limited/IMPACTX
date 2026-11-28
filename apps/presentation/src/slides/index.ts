import type { SlideMeta } from "../types";
import Slide01Hero from "./Slide01Hero";
import Slide02Problem from "./Slide02Problem";
import Slide03Solution from "./Slide03Solution";
import Slide04Story from "./Slide04Story";
import Slide05Safety from "./Slide05Safety";
import Slide06Sync from "./Slide06Sync";
import Slide07Storage from "./Slide07Storage";
import Slide08EdgeAI from "./Slide08EdgeAI";
import Slide09IndiaReady from "./Slide09IndiaReady";
import Slide10Moats from "./Slide10Moats";
import Slide11Scale from "./Slide11Scale";
import Slide12Closing from "./Slide12Closing";

export const SLIDES: SlideMeta[] = [
  {
    id: "slide-01-hero",
    number: 1,
    title: "Aarogya Mesh · आरोग्य संजाल",
    subtitle: "Zero-cloud, offline-first clinical intelligence for rural Bharat",
    speakerNotes: [
      "Namaste everyone — meet Aarogya Mesh (आरोग्य संजाल): an offline-first clinical mesh built for rural India.",
      "Every feature you will see today works 100% in Airplane Mode — zero cloud, zero SIM signal required.",
      "Press T anytime if you want to switch between Obsidian Dark and Daylight Projector Light mode.",
    ],
    component: Slide01Hero,
  },
  {
    id: "slide-02-problem",
    number: 2,
    title: "The Last-Mile Reality in Rural India",
    subtitle: "Why cloud health apps fail when an ASHA didi needs them most",
    speakerNotes: [
      "Over 10 lakh ASHA didis serve rural India — often in villages with zero 4G and frequent power cuts.",
      "When a high-risk mother or newborn has a danger sign at 2 AM, a loading spinner is not an inconvenience — it costs the golden hour.",
      "Paper registers get delayed by weeks, so doctors at the PHC never see village outbreaks or high-risk alerts in time.",
    ],
    component: Slide02Problem,
  },
  {
    id: "slide-03-solution",
    number: 3,
    title: "Our 3-Tier Offline Mesh",
    subtitle: "Family Watch → ASHA Phone → PHC Clinic Laptop — zero cloud needed",
    speakerNotes: [
      "We designed a 3-tier mesh that mirrors how rural healthcare actually works on the ground.",
      "Tier 0 is a simple 2-tap Family Watch (or ₹0 family phone mode) for instant SOS.",
      "Tier 1 is the ASHA didi's Android phone — works completely offline in the village.",
      "Tier 2 is the Primary Health Centre (PHC) laptop — auto-syncs the moment she walks into clinic Wi-Fi.",
    ],
    component: Slide03Solution,
  },
  {
    id: "slide-04-story",
    number: 4,
    title: "A Day in Rampur Village",
    subtitle: "From a 2 AM offline SOS to a 108 ambulance in four seamless steps",
    speakerNotes: [
      "Walk through Sunita Devi's story in Rampur village: she is 30 weeks pregnant and feels sudden danger signs at home.",
      "Step 1: 2-tap SOS fires offline in 0 ms. Step 2: ASHA didi runs the WHO check and records a Hindi voice note in Airplane Mode.",
      "Step 3: At the PHC hotspot, her phone syncs automatically. Step 4: The doctor sees crystal-clear risk cards and dispatches a 108 ambulance.",
    ],
    component: Slide04Story,
  },
  {
    id: "slide-05-safety",
    number: 5,
    title: "Why AI Alone Is Dangerous — Our Safety Shield",
    subtitle: "Immutable WHO IMNCI + NHM clinical floor below local AI assistance",
    speakerNotes: [
      "In healthcare, a hallucinating LLM that downgrades an emergency can cost a life.",
      "Our bottom layer is an immutable deterministic floor: official WHO IMNCI, NHM ASHA, and India UIP rules running in under 1 millisecond.",
      "Our local AI sits strictly on top to extract symptoms and explain risk — and is mathematically blocked from ever downgrading a RED emergency.",
    ],
    component: Slide05Safety,
  },
  {
    id: "slide-06-sync",
    number: 6,
    title: "Smart Sync Without Internet",
    subtitle: "Interactive conflict-free merge when two offline devices edit at once",
    speakerNotes: [
      "What happens if the ASHA phone updates ANC Visit 3 while the Family Watch triggers a Bleeding SOS at the exact same second offline?",
      "Click 'Simulate Merge' right on this slide: our field-level CRDT merge combines both records into one unified patient timeline.",
      "Zero overwrites, zero lost emergencies, zero manual conflict resolution.",
    ],
    component: Slide06Sync,
  },
  {
    id: "slide-07-storage",
    number: 7,
    title: "Where Your Data Lives (Zero Cloud)",
    subtitle: "100% sovereign on-device & clinic storage — DPDP Act 2023 by design",
    speakerNotes: [
      "Every byte of patient data stays inside the community: Watch local storage, ASHA phone's private loopback APK storage, and one SQLite database on the PHC laptop.",
      "Cloud bytes stored: literally zero. No external APIs, no vendor lock-in, and naturally compliant with India's DPDP Act 2023.",
    ],
    component: Slide07Storage,
  },
  {
    id: "slide-08-edge-ai",
    number: 8,
    title: "Smart AI on a Normal Clinic Laptop",
    subtitle: "5-stage CPU-only pipeline: Voice → Negation-Safe AI → Risk Bars & Outbreak Radar",
    speakerNotes: [
      "Rural PHCs don't have ₹5 lakh GPUs — they have normal clinic laptops.",
      "Our 5-stage pipeline converts Hindi or English voice into clean text, handles negations safely ('no fever' is never misread as fever), checks WHO rules, and renders explainable + / - risk bars.",
      "At the village level, it spots fever clusters early — like our Rampur outbreak radar.",
    ],
    component: Slide08EdgeAI,
  },
  {
    id: "slide-09-india-ready",
    number: 9,
    title: "Built for Real Bharat",
    subtitle: "Shuddh Tatsama Hindi, 2-tap accidental-proof SOS, and signed Android APK",
    speakerNotes: [
      "Three details judges love: first, pure Shuddh Tatsama Hindi (ज्वर, श्वास कष्ट, आपातकाल) — zero broken Hinglish.",
      "Second, a 2-tap confirmation on Watch and ₹0 Phone SOS so there are no accidental 108 calls.",
      "Third, a real signed Android APK tested on a Samsung Galaxy S23 in full Airplane Mode with mic and haptics.",
    ],
    component: Slide09IndiaReady,
  },
  {
    id: "slide-10-moats",
    number: 10,
    title: "Why This Isn't Just a Phone UI",
    subtitle: "952 passing tests, 341 WHO parity checks, 12.8 KiB ML model, 0 cloud calls",
    speakerNotes: [
      "Under the hood, this is production-grade engineering: 952 automated tests and 341 WHO clinical parity checks passing.",
      "Our trained risk model is just 12.8 KiB — zero PyTorch bloat, runs in milliseconds on any CPU.",
      "Every claim on this slide is verifiable in our live repo and test suite.",
    ],
    component: Slide10Moats,
  },
  {
    id: "slide-11-scale",
    number: 11,
    title: "Affordable at National Scale",
    subtitle: "Rotated ₹1,500 PHC wristbands, ₹0 family Android mode, ABDM & RCH ready",
    speakerNotes: [
      "How does this scale across India without breaking state health budgets?",
      "Each PHC loans a ₹1,500 wristband only to high-risk mothers in their final 8 weeks, then sanitizes and rotates it — plus ₹0 family Android mode for everyone else.",
      "Whenever town broadband is available, the PHC laptop bridges cleanly to India's ABDM and RCH portals.",
    ],
    component: Slide11Scale,
  },
  {
    id: "slide-12-closing",
    number: 12,
    title: "Live Demo & Thank You · धन्यवाद",
    subtitle: "Life-saving clinical intelligence for the last disconnected mile",
    speakerNotes: [
      "To wrap up: Aarogya Mesh brings life-saving clinical intelligence to the last disconnected mile.",
      "Now let's switch directly to our live 3-tier demo — Airplane Mode SOS, Hindi voice to explainable AI risk bars, and zero-loss sync.",
      "Click 'Open Live 3-Tier Demo' to launch the live showcase. धन्यवाद!",
    ],
    component: Slide12Closing,
  },
];
