import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  ShieldCheck,
  CloudOff,
  Cpu,
  Zap,
  RefreshCw,
  Languages,
  Lock,
  Layers,
} from "lucide-react";
import type { SlideProps } from "../types";

interface AnimatedStatProps {
  target: number;
  decimals?: number;
  suffix?: string;
  isActive: boolean;
}

function AnimatedStat({
  target,
  decimals = 0,
  suffix = "",
  isActive,
}: AnimatedStatProps) {
  const [val, setVal] = useState(target);

  useEffect(() => {
    if (!isActive || target === 0) {
      setVal(target);
      return;
    }
    let frameId = 0;
    const duration = 900;
    const start = performance.now();

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setVal(target * eased);
      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      }
    };

    setVal(0);
    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [isActive, target]);

  const formatted =
    decimals > 0 ? val.toFixed(decimals) : Math.round(val).toString();

  return (
    <>
      {formatted}
      {suffix}
    </>
  );
}

const METRICS = [
  {
    target: 952,
    decimals: 0,
    suffix: "",
    label: "Passing Tests",
    sub: "End-to-end verified",
    accent: "var(--accent-emerald)",
    icon: CheckCircle2,
  },
  {
    target: 341,
    decimals: 0,
    suffix: "",
    label: "WHO Parity Checks",
    sub: "Clinical safety rules",
    accent: "var(--accent-cyan)",
    icon: ShieldCheck,
  },
  {
    target: 0,
    decimals: 0,
    suffix: "",
    label: "Cloud API Calls",
    sub: "Zero external runtime",
    accent: "var(--accent-rose)",
    icon: CloudOff,
  },
  {
    target: 12.8,
    decimals: 1,
    suffix: " KiB",
    label: "Trained ML Model",
    sub: "Calibrated edge weights",
    accent: "var(--accent-saffron)",
    icon: Cpu,
  },
  {
    target: 0,
    decimals: 0,
    suffix: "",
    label: "PyTorch Bloat",
    sub: "Pure lightweight CPU",
    accent: "var(--accent-emerald)",
    icon: Zap,
  },
];

const PILLARS = [
  {
    title: "WHO Clinical Safety Floor",
    desc: "Deterministic maternal & pediatric danger rules always override ML — zero missed red flags.",
    icon: ShieldCheck,
    accent: "var(--accent-rose)",
  },
  {
    title: "Tiny 12.8 KiB Edge Inference",
    desc: "Runs instantly on a 10-year-old PHC clinic laptop without GPUs, Docker bloat, or PyTorch.",
    icon: Cpu,
    accent: "var(--accent-saffron)",
  },
  {
    title: "Zero-Loss Idempotent Sync",
    desc: "Outbox queue guarantees zero duplicate patients and zero dropped SOS alerts on flaky 2G.",
    icon: RefreshCw,
    accent: "var(--accent-cyan)",
  },
  {
    title: "Negation-Safe Hindi NLP",
    desc: "Understands clinical Hindi negations accurately so 'no fever' never triggers false panic.",
    icon: Languages,
    accent: "var(--accent-emerald)",
  },
  {
    title: "True 3-Tier Sovereign Stack",
    desc: "Real Watch + signed Android APK + local FastAPI/SQLite Hub — not a mocked web prototype.",
    icon: Lock,
    accent: "var(--accent-saffron)",
  },
];

export default function Slide10Moats({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";

  return (
    <div
      className="slide-frame"
      style={{
        width: "100%",
        height: "100%",
        maxWidth: 1260,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 18,
        padding: "14px 28px 68px",
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -14 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: -14 }}
        transition={{ duration: 0.4 }}
        style={{ display: "flex", flexDirection: "column", gap: 6 }}
      >
        <div>
          <span
            className="pill"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "var(--accent-emerald)",
              borderColor: "var(--accent-emerald)",
            }}
          >
            <Layers size={13} />
            Deep Engineering Moats · Battle-Tested
          </span>
        </div>

        <h1
          style={{
            margin: 0,
            fontSize: "clamp(26px, 3.3vw, 42px)",
            fontWeight: 800,
            lineHeight: 1.12,
            letterSpacing: "-0.02em",
            color: "var(--text)",
          }}
        >
          Why This Isn&apos;t{" "}
          <span className="gradient-text">&ldquo;Just a Phone UI&rdquo;</span>
        </h1>
      </motion.div>

      {/* Top Row: 5 High-Impact Animated Counter Bento Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 12,
        }}
      >
        {METRICS.map((m, idx) => {
          const Icon = m.icon;
          return (
            <motion.div
              key={m.label}
              className="glass-card"
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={
                isActive
                  ? { opacity: 1, y: 0, scale: 1 }
                  : { opacity: 0, y: 20, scale: 0.95 }
              }
              transition={{
                delay: 0.1 + idx * 0.08,
                type: "spring",
                stiffness: 190,
                damping: 20,
              }}
              style={{
                padding: "16px 14px",
                display: "flex",
                flexDirection: "column",
                gap: 6,
                borderTop: `3px solid ${m.accent}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  Verified
                </span>
                <Icon size={16} style={{ color: m.accent }} />
              </div>

              <div
                className="metric-value"
                style={{
                  fontSize: "clamp(26px, 2.7vw, 36px)",
                  fontWeight: 900,
                  lineHeight: 1.05,
                  color: m.accent,
                }}
              >
                <AnimatedStat
                  target={m.target}
                  decimals={m.decimals}
                  suffix={m.suffix}
                  isActive={isActive}
                />
              </div>

              <div
                style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: "var(--text)",
                  lineHeight: 1.2,
                }}
              >
                {m.label}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {m.sub}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Bottom Bento: 5 Plain-English Engineering Pillars */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gap: 12,
        }}
      >
        {PILLARS.map((p, idx) => {
          const Icon = p.icon;
          const span = idx < 3 ? "span 2" : "span 3";
          return (
            <motion.div
              key={p.title}
              className="glass-card"
              initial={{ opacity: 0, y: 18 }}
              animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 18 }}
              transition={{ delay: 0.42 + idx * 0.07, duration: 0.4 }}
              style={{
                gridColumn: span,
                padding: "16px 18px",
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 10,
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: isDark
                    ? "rgba(255,255,255,0.06)"
                    : "rgba(15,23,42,0.06)",
                  color: p.accent,
                }}
              >
                <Icon size={18} />
              </div>

              <div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "var(--text)",
                    marginBottom: 4,
                  }}
                >
                  {p.title}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    lineHeight: 1.45,
                    color: "var(--text-muted)",
                  }}
                >
                  {p.desc}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
