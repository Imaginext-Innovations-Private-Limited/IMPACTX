import React from "react";
import { motion } from "framer-motion";
import {
  ShieldAlert,
  ShieldCheck,
  Lock,
  Brain,
  CheckCircle2,
  XCircle,
  Sparkles,
} from "lucide-react";
import type { SlideProps } from "../types";

export default function Slide05Safety({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";

  return (
    <div className="slide-frame" style={{ gap: 20 }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
        transition={{ duration: 0.55 }}
      >
        <span
          className="pill"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 14px",
            fontSize: "0.82rem",
            fontWeight: 700,
            color: "var(--accent-emerald)",
            background: isDark
              ? "rgba(16, 185, 129, 0.14)"
              : "rgba(5, 150, 105, 0.1)",
          }}
        >
          <ShieldCheck size={14} />
          <span>CLINICAL SAFETY ARCHITECTURE · सुरक्षा कवच</span>
        </span>
        <h2
          style={{
            fontSize: "clamp(1.95rem, 3.4vw, 2.85rem)",
            fontWeight: 800,
            margin: "10px 0 4px 0",
            letterSpacing: "-0.03em",
            color: "var(--text)",
            lineHeight: 1.12,
          }}
        >
          Why AI Alone Is Dangerous —{" "}
          <span className="gradient-text">Our 2-Layer Safety Shield</span>
        </h2>
        <p
          style={{
            margin: 0,
            fontSize: "0.98rem",
            color: "var(--text-muted)",
            maxWidth: 780,
          }}
        >
          AI models can occasionally guess wrong. In maternal &amp; newborn care,
          a single wrong guess costs a life — so our AI assists, but{" "}
          <strong style={{ color: "var(--text)" }}>
            WHO clinical rules always hold the floor.
          </strong>
        </p>
      </motion.div>

      {/* Main 2-Column Layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.12fr 0.88fr",
          gap: 22,
          alignItems: "stretch",
        }}
      >
        {/* Left: 2-Layer Animated Shield Stack */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Top Layer: Local AI Helper */}
          <motion.div
            className="glass-card"
            initial={{ opacity: 0, y: -18 }}
            animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: -10 }}
            transition={{ duration: 0.55, delay: 0.14 }}
            style={{
              padding: "20px 22px",
              borderRadius: 20,
              borderLeft: "4px solid var(--accent-cyan)",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 11,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isDark
                      ? "rgba(6, 182, 212, 0.16)"
                      : "rgba(8, 145, 178, 0.12)",
                    color: "var(--accent-cyan)",
                  }}
                >
                  <Brain size={20} />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 750,
                      letterSpacing: "0.06em",
                      color: "var(--accent-cyan)",
                    }}
                  >
                    TOP LAYER · ASSISTIVE INTELLIGENCE
                  </div>
                  <div
                    style={{
                      fontSize: "1.1rem",
                      fontWeight: 780,
                      color: "var(--text)",
                    }}
                  >
                    Local On-Device AI Helper
                  </div>
                </div>
              </div>
              <span
                className="pill"
                style={{
                  fontSize: "0.74rem",
                  fontWeight: 700,
                  padding: "4px 10px",
                  color: "var(--accent-cyan)",
                }}
              >
                Can Upgrade Only
              </span>
            </div>
            <p
              style={{
                margin: 0,
                fontSize: "0.9rem",
                lineHeight: 1.5,
                color: "var(--text-muted)",
              }}
            >
              Extracts symptoms from Hindi &amp; English voice notes, scores
              visual risk bars, and drafts clear next-step care reminders —
              100% offline.
            </p>
          </motion.div>

          {/* Animated Hard Safety Lock Divider */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={isActive ? { opacity: 1, scale: 1 } : { opacity: 0.5, scale: 0.96 }}
            transition={{ duration: 0.5, delay: 0.28 }}
            style={{
              padding: "11px 18px",
              borderRadius: 14,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              background: isDark
                ? "linear-gradient(90deg, rgba(244,63,94,0.18), rgba(245,158,11,0.2), rgba(16,185,129,0.18))"
                : "linear-gradient(90deg, rgba(225,29,72,0.12), rgba(217,119,6,0.14), rgba(5,150,105,0.12))",
              border: "1.5px solid var(--accent-saffron)",
              fontSize: "0.86rem",
              fontWeight: 780,
              color: "var(--text)",
            }}
          >
            <motion.span
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              style={{ display: "inline-flex", color: "var(--accent-saffron)" }}
            >
              <Lock size={16} />
            </motion.span>
            <span>
              HARD MONOTONIC GUARD: AI is mathematically blocked from ever
              downgrading a RED emergency
            </span>
          </motion.div>

          {/* Bottom Layer: Immutable WHO Floor */}
          <motion.div
            className="glass-card"
            initial={{ opacity: 0, y: 18 }}
            animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
            transition={{ duration: 0.55, delay: 0.34 }}
            style={{
              padding: "22px 22px",
              borderRadius: 20,
              borderLeft: "4px solid var(--accent-emerald)",
              borderColor: isDark
                ? "rgba(16, 185, 129, 0.42)"
                : "rgba(5, 150, 105, 0.38)",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 11,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isDark
                      ? "rgba(16, 185, 129, 0.18)"
                      : "rgba(5, 150, 105, 0.14)",
                    color: "var(--accent-emerald)",
                  }}
                >
                  <ShieldCheck size={22} />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 750,
                      letterSpacing: "0.06em",
                      color: "var(--accent-emerald)",
                    }}
                  >
                    BOTTOM IMMUTABLE FLOOR · NEVER HALLUCINATES
                  </div>
                  <div
                    style={{
                      fontSize: "1.14rem",
                      fontWeight: 800,
                      color: "var(--text)",
                    }}
                  >
                    WHO IMNCI + NHM ASHA + India UIP Rules
                  </div>
                </div>
              </div>
              <span
                className="pill"
                style={{
                  fontSize: "0.76rem",
                  fontWeight: 800,
                  padding: "5px 11px",
                  color: "var(--accent-emerald)",
                }}
              >
                &lt; 1 ms
              </span>
            </div>

            <p
              style={{
                margin: 0,
                fontSize: "0.91rem",
                lineHeight: 1.52,
                color: "var(--text-muted)",
              }}
            >
              Pure deterministic medical rules verified against Indian public
              health guidelines. Runs in under 1 millisecond on every device —
              zero probability, zero guesswork.
            </p>
          </motion.div>
        </div>

        {/* Right: Concrete Proof Scenario Card */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, x: 20 }}
          animate={isActive ? { opacity: 1, x: 0 } : { opacity: 0.4, x: 12 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          style={{
            padding: "22px 22px",
            borderRadius: 22,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ShieldAlert size={18} style={{ color: "var(--accent-rose)" }} />
              <span
                style={{
                  fontSize: "0.82rem",
                  fontWeight: 800,
                  letterSpacing: "0.05em",
                  color: "var(--text-muted)",
                }}
              >
                SAFETY PROOF IN ACTION
              </span>
            </div>

            {/* Patient Input */}
            <div
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                background: isDark
                  ? "rgba(255,255,255,0.04)"
                  : "rgba(15,23,42,0.04)",
                border: "1px solid var(--surface-border)",
              }}
            >
              <div
                style={{
                  fontSize: "0.74rem",
                  fontWeight: 700,
                  color: "var(--text-muted)",
                  marginBottom: 4,
                }}
              >
                PATIENT SIGNALS
              </div>
              <div
                style={{
                  fontSize: "0.94rem",
                  fontWeight: 650,
                  color: "var(--text)",
                }}
              >
                &ldquo;Week 30 · Severe vaginal bleeding + blurred vision&rdquo;
              </div>
            </div>

            {/* WHO Floor Decision */}
            <div
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                background: isDark
                  ? "rgba(244, 63, 94, 0.14)"
                  : "rgba(225, 29, 72, 0.09)",
                border: "1px solid var(--accent-rose)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "0.74rem",
                    fontWeight: 750,
                    color: "var(--accent-rose)",
                  }}
                >
                  1. WHO SAFETY FLOOR (0.4 ms)
                </div>
                <div
                  style={{
                    fontSize: "0.98rem",
                    fontWeight: 800,
                    color: "var(--text)",
                  }}
                >
                  RED — Immediate 108 Referral
                </div>
              </div>
              <Lock size={18} style={{ color: "var(--accent-rose)" }} />
            </div>

            {/* Hypothetical AI Downgrade Attempt */}
            <div
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                background: isDark
                  ? "rgba(255,255,255,0.03)"
                  : "rgba(15,23,42,0.03)",
                border: "1px dashed var(--surface-border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "0.74rem",
                    fontWeight: 700,
                    color: "var(--text-muted)",
                  }}
                >
                  2. EVEN IF AN AI MODEL SUGGESTS...
                </div>
                <div
                  style={{
                    fontSize: "0.92rem",
                    color: "var(--text-muted)",
                    textDecoration: "line-through",
                  }}
                >
                  &ldquo;Yellow — Monitor at home&rdquo;
                </div>
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  fontSize: "0.76rem",
                  fontWeight: 800,
                  color: "var(--accent-rose)",
                }}
              >
                <XCircle size={15} />
                BLOCKED
              </span>
            </div>

            {/* Final Guaranteed Result */}
            <div
              style={{
                padding: "14px 16px",
                borderRadius: 14,
                background: isDark
                  ? "rgba(16, 185, 129, 0.14)"
                  : "rgba(5, 150, 105, 0.1)",
                border: "1.5px solid var(--accent-emerald)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "0.74rem",
                    fontWeight: 800,
                    color: "var(--accent-emerald)",
                  }}
                >
                  3. GUARANTEED FINAL OUTPUT
                </div>
                <div
                  style={{
                    fontSize: "1.02rem",
                    fontWeight: 800,
                    color: "var(--text)",
                  }}
                >
                  RED EMERGENCY LOCKED + AI Notes Attached
                </div>
              </div>
              <CheckCircle2 size={22} style={{ color: "var(--accent-emerald)" }} />
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              paddingTop: 10,
              borderTop: "1px solid var(--surface-border)",
              fontSize: "0.8rem",
              color: "var(--text-muted)",
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Sparkles size={14} style={{ color: "var(--accent-saffron)" }} />
              341 automated WHO parity tests
            </span>
            <strong style={{ color: "var(--accent-emerald)" }}>
              0 Hallucinations
            </strong>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
