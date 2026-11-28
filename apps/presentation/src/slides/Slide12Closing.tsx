import { motion } from "framer-motion";
import {
  Plane,
  Mic,
  Radio,
  ArrowRight,
  HeartPulse,
  Sparkles,
} from "lucide-react";
import type { SlideProps } from "../types";

const DEMO_STEPS = [
  {
    num: "01",
    title: "Airplane Mode SOS",
    desc: "Trigger a 2-tap emergency alert from the watch/phone with zero internet.",
    icon: Plane,
    accent: "var(--accent-rose)",
  },
  {
    num: "02",
    title: "Voice → AI Risk Bars",
    desc: "Speak clinical Hindi and watch WHO rules + SHAP risk bars render in <15ms.",
    icon: Mic,
    accent: "var(--accent-saffron)",
  },
  {
    num: "03",
    title: "Outbreak + Zero-Loss Sync",
    desc: "See the Rampur cluster radar light up and queued records sync cleanly.",
    icon: Radio,
    accent: "var(--accent-emerald)",
  },
];

export default function Slide12Closing({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";

  return (
    <div
      className="slide-frame"
      style={{
        width: "100%",
        height: "100%",
        maxWidth: 1220,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        gap: 24,
        padding: "16px 28px 72px",
        boxSizing: "border-box",
      }}
    >
      {/* Top Tag */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: -12 }}
        transition={{ duration: 0.4 }}
      >
        <span
          className="pill"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            fontSize: 12.5,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--accent-saffron)",
            borderColor: "var(--accent-saffron)",
          }}
        >
          <HeartPulse size={14} />
          Aarogya Mesh · आरोग्य संजाल · Live Demo
        </span>
      </motion.div>

      {/* धन्यवाद + Punchline */}
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={
          isActive ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.94 }
        }
        transition={{ delay: 0.1, type: "spring", stiffness: 160, damping: 18 }}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          className="gradient-text"
          style={{
            fontSize: "clamp(48px, 6vw, 76px)",
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: "-0.02em",
          }}
        >
          धन्यवाद
        </div>

        <h1
          style={{
            margin: 0,
            fontSize: "clamp(22px, 2.5vw, 32px)",
            fontWeight: 800,
            lineHeight: 1.25,
            color: "var(--text)",
            maxWidth: 820,
          }}
        >
          &ldquo;Life-saving clinical intelligence for the last disconnected
          mile.&rdquo;
        </h1>
      </motion.div>

      {/* 3-Step Live Demo Cue Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
          width: "100%",
          textAlign: "left",
        }}
      >
        {DEMO_STEPS.map((step, idx) => {
          const Icon = step.icon;
          return (
            <motion.div
              key={step.num}
              className="glass-card"
              initial={{ opacity: 0, y: 22 }}
              animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 22 }}
              transition={{
                delay: 0.22 + idx * 0.1,
                type: "spring",
                stiffness: 175,
                damping: 20,
              }}
              style={{
                padding: "18px 18px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                borderTop: `3px solid ${step.accent}`,
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
                    fontSize: 12,
                    fontWeight: 900,
                    letterSpacing: "0.08em",
                    color: step.accent,
                  }}
                >
                  DEMO STEP {step.num}
                </span>
                <Icon size={18} style={{ color: step.accent }} />
              </div>

              <div
                style={{
                  fontSize: 17,
                  fontWeight: 800,
                  color: "var(--text)",
                }}
              >
                {step.title}
              </div>
              <div
                style={{
                  fontSize: 13,
                  lineHeight: 1.48,
                  color: "var(--text-muted)",
                }}
              >
                {step.desc}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Glowing Interactive CTA Button to /showcase */}
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 18 }}
        transition={{ delay: 0.52, duration: 0.4 }}
        style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}
      >
        <motion.a
          href="/showcase"
          whileHover={{ scale: 1.04, y: -2 }}
          whileTap={{ scale: 0.98 }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "16px 32px",
            borderRadius: 999,
            textDecoration: "none",
            fontSize: 17,
            fontWeight: 800,
            letterSpacing: "0.01em",
            color: "#071018",
            background:
              "linear-gradient(135deg, var(--accent-saffron) 0%, var(--accent-emerald) 100%)",
            boxShadow: isDark
              ? "0 0 34px -4px rgba(245, 158, 11, 0.55), 0 10px 26px -8px rgba(16, 185, 129, 0.5)"
              : "0 12px 30px -8px rgba(16, 185, 129, 0.45), 0 6px 18px -6px rgba(245, 158, 11, 0.45)",
            cursor: "pointer",
          }}
        >
          <Sparkles size={19} />
          <span>Open Live 3-Tier Demo</span>
          <ArrowRight size={19} />
        </motion.a>

        <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
          Runs locally at{" "}
          <code
            style={{
              fontFamily:
                "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              color: "var(--text)",
              fontWeight: 600,
            }}
          >
            /showcase
          </code>{" "}
          · Zero internet required
        </span>
      </motion.div>
    </div>
  );
}
