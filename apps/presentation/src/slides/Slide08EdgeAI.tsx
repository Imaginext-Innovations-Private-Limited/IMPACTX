import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Mic,
  FileText,
  Filter,
  ShieldAlert,
  BarChart3,
  Cpu,
  Radio,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";
import type { SlideProps } from "../types";

const PIPELINE_STAGES = [
  {
    step: "01",
    label: "Hindi / English Voice",
    sub: "Local audio capture",
    icon: Mic,
    color: "var(--accent-saffron)",
  },
  {
    step: "02",
    label: "Clean Text",
    sub: "Offline normalize",
    icon: FileText,
    color: "var(--accent-cyan)",
  },
  {
    step: "03",
    label: "Negation-Safe Extract",
    sub: '"बुखार नहीं" ≠ Fever',
    icon: Filter,
    color: "var(--accent-emerald)",
  },
  {
    step: "04",
    label: "WHO Safety Check",
    sub: "Hard red-flag floor",
    icon: ShieldAlert,
    color: "var(--accent-rose)",
  },
  {
    step: "05",
    label: "Risk Bars + Radar",
    sub: "Explainable output",
    icon: BarChart3,
    color: "var(--accent-saffron)",
  },
];

const RISK_FACTORS = [
  { label: "BP 162/104 mmHg (Severe)", value: +0.38, pct: 86, positive: true },
  { label: "Headache + Blurred Vision", value: +0.29, pct: 66, positive: true },
  { label: "36 Weeks Gestation", value: +0.18, pct: 44, positive: true },
  { label: "No Convulsions Reported", value: -0.11, pct: 32, positive: false },
  { label: "Conscious & Alert", value: -0.07, pct: 22, positive: false },
];

export default function Slide08EdgeAI({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    if (!isActive) return;
    const timer = window.setInterval(() => {
      setActiveStage((prev) => (prev + 1) % PIPELINE_STAGES.length);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [isActive]);

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
              color: "var(--accent-cyan)",
              borderColor: "var(--accent-cyan)",
            }}
          >
            <Cpu size={13} />
            Explainable Edge AI · CPU-Only · Runs Under 15 ms
          </span>
        </div>

        <h1
          style={{
            margin: 0,
            fontSize: "clamp(26px, 3.2vw, 42px)",
            fontWeight: 800,
            lineHeight: 1.12,
            letterSpacing: "-0.02em",
            color: "var(--text)",
          }}
        >
          Smart AI on a Normal Clinic Laptop{" "}
          <span className="gradient-text">(No GPU Needed)</span>
        </h1>
      </motion.div>

      {/* 5-Stage Animated Pipeline */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr auto 1fr auto 1fr auto 1fr",
          alignItems: "center",
          gap: 8,
        }}
      >
        {PIPELINE_STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const highlighted = activeStage === idx;
          return (
            <React.Fragment key={stage.step}>
              <motion.div
                className="glass-card"
                initial={{ opacity: 0, y: 16 }}
                animate={
                  isActive
                    ? {
                        opacity: 1,
                        y: 0,
                        scale: highlighted ? 1.03 : 1,
                      }
                    : { opacity: 0, y: 16 }
                }
                transition={{
                  delay: 0.08 + idx * 0.07,
                  duration: 0.35,
                }}
                style={{
                  padding: "12px 12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  borderColor: highlighted
                    ? stage.color
                    : "var(--surface-border)",
                  boxShadow: highlighted
                    ? `0 0 22px -6px ${stage.color}`
                    : undefined,
                  transition: "border-color 0.3s ease, box-shadow 0.3s ease",
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
                      fontWeight: 800,
                      color: stage.color,
                      letterSpacing: "0.08em",
                    }}
                  >
                    STAGE {stage.step}
                  </span>
                  <Icon size={17} style={{ color: stage.color }} />
                </div>
                <div
                  style={{
                    fontSize: 13.5,
                    fontWeight: 700,
                    color: "var(--text)",
                    lineHeight: 1.25,
                  }}
                >
                  {stage.label}
                </div>
                <div
                  style={{
                    fontSize: 11.5,
                    color: "var(--text-muted)",
                    lineHeight: 1.3,
                  }}
                >
                  {stage.sub}
                </div>
              </motion.div>

              {idx < PIPELINE_STAGES.length - 1 && (
                <ArrowRight
                  size={16}
                  style={{
                    color:
                      activeStage === idx
                        ? "var(--accent-saffron)"
                        : "var(--text-muted)",
                    opacity: activeStage === idx ? 1 : 0.45,
                    transition: "all 0.3s ease",
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Bottom Split: SHAP Explainable Risk Bars + Village Outbreak Radar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.35fr 1fr",
          gap: 18,
          alignItems: "stretch",
        }}
      >
        {/* Left: Animated SHAP-style Risk Bars */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, x: -20 }}
          animate={isActive ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
          transition={{ delay: 0.35, duration: 0.45 }}
          style={{
            padding: "18px 20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 10,
            }}
          >
            <div>
              <div
                style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}
              >
                Explainable Risk Bars (Zero Black Box)
              </div>
              <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
                Doctors see exact <strong style={{ color: "var(--accent-rose)" }}>+ Risk</strong>{" "}
                and <strong style={{ color: "var(--accent-emerald)" }}>− Protective</strong>{" "}
                clinical drivers
              </div>
            </div>

            <span
              className="pill"
              style={{
                fontSize: 12,
                fontWeight: 800,
                color: "var(--accent-rose)",
                borderColor: "var(--accent-rose)",
                background: isDark
                  ? "rgba(244,63,94,0.14)"
                  : "rgba(225,29,72,0.1)",
              }}
            >
              RED · 87% RISK
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {RISK_FACTORS.map((item, idx) => (
              <div
                key={item.label}
                style={{
                  display: "grid",
                  gridTemplateColumns: "195px 1fr 54px",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <span
                  style={{
                    fontSize: 12.5,
                    fontWeight: 600,
                    color: "var(--text)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {item.label}
                </span>

                {/* Diverging Bar Track */}
                <div
                  style={{
                    height: 12,
                    borderRadius: 999,
                    background: isDark
                      ? "rgba(255,255,255,0.06)"
                      : "rgba(15,23,42,0.07)",
                    position: "relative",
                    overflow: "hidden",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  {/* Center zero divider */}
                  <div
                    style={{
                      position: "absolute",
                      left: "42%",
                      top: 0,
                      bottom: 0,
                      width: 1.5,
                      background: "var(--text-muted)",
                      opacity: 0.4,
                    }}
                  />
                  {item.positive ? (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={
                        isActive
                          ? { width: `${item.pct * 0.56}%` }
                          : { width: 0 }
                      }
                      transition={{
                        delay: 0.45 + idx * 0.08,
                        duration: 0.6,
                        ease: "easeOut",
                      }}
                      style={{
                        position: "absolute",
                        left: "42%",
                        height: "100%",
                        borderRadius: "0 999px 999px 0",
                        background:
                          "linear-gradient(90deg, var(--accent-saffron), var(--accent-rose))",
                      }}
                    />
                  ) : (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={
                        isActive
                          ? { width: `${item.pct * 0.4}%` }
                          : { width: 0 }
                      }
                      transition={{
                        delay: 0.45 + idx * 0.08,
                        duration: 0.6,
                        ease: "easeOut",
                      }}
                      style={{
                        position: "absolute",
                        right: "58%",
                        height: "100%",
                        borderRadius: "999px 0 0 999px",
                        background:
                          "linear-gradient(270deg, var(--accent-emerald), var(--accent-cyan))",
                      }}
                    />
                  )}
                </div>

                <span
                  style={{
                    fontSize: 12.5,
                    fontWeight: 800,
                    textAlign: "right",
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    color: item.positive
                      ? "var(--accent-rose)"
                      : "var(--accent-emerald)",
                  }}
                >
                  {item.positive ? `+${item.value.toFixed(2)}` : item.value.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Right: Village Outbreak Radar */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, x: 20 }}
          animate={isActive ? { opacity: 1, x: 0 } : { opacity: 0, x: 20 }}
          transition={{ delay: 0.42, duration: 0.45 }}
          style={{
            padding: "18px 20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 10,
            borderTop: "3px solid var(--accent-rose)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Radio size={18} style={{ color: "var(--accent-rose)" }} />
              <span
                style={{ fontSize: 16, fontWeight: 700, color: "var(--text)" }}
              >
                Village Outbreak Radar
              </span>
            </div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 800,
                color: "var(--accent-saffron)",
                letterSpacing: "0.06em",
              }}
            >
              LIVE CLUSTER
            </span>
          </div>

          {/* Pulsing SVG Radar Map */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              height: 146,
            }}
          >
            <svg viewBox="0 0 280 146" style={{ width: "100%", height: "100%" }}>
              {/* Radar rings around Rampur */}
              {[24, 46, 68].map((r, i) => (
                <motion.circle
                  key={r}
                  cx="138"
                  cy="74"
                  r={r}
                  fill="none"
                  stroke="var(--accent-rose)"
                  strokeWidth="1.2"
                  strokeDasharray={i === 2 ? "4 4" : undefined}
                  initial={{ opacity: 0.18 }}
                  animate={
                    isActive
                      ? { opacity: [0.15, 0.55, 0.15], scale: [0.97, 1.04, 0.97] }
                      : {}
                  }
                  transition={{
                    repeat: Infinity,
                    duration: 2.6,
                    delay: i * 0.45,
                  }}
                  style={{ transformOrigin: "138px 74px" }}
                />
              ))}

              {/* Connecting lines to neighboring villages */}
              <line
                x1="138"
                y1="74"
                x2="48"
                y2="42"
                stroke="var(--surface-border)"
                strokeWidth="1.5"
                strokeDasharray="3 3"
              />
              <line
                x1="138"
                y1="74"
                x2="232"
                y2="108"
                stroke="var(--surface-border)"
                strokeWidth="1.5"
                strokeDasharray="3 3"
              />

              {/* Calm village 1 */}
              <circle cx="48" cy="42" r="6" fill="var(--accent-emerald)" />
              <text
                x="48"
                y="28"
                textAnchor="middle"
                fill="var(--text-muted)"
                fontSize="10.5"
                fontWeight="600"
              >
                Sitapur (Calm)
              </text>

              {/* Calm village 2 */}
              <circle cx="232" cy="108" r="6" fill="var(--accent-emerald)" />
              <text
                x="232"
                y="128"
                textAnchor="middle"
                fill="var(--text-muted)"
                fontSize="10.5"
                fontWeight="600"
              >
                Devgarh (Calm)
              </text>

              {/* Rampur pulsing hotspot */}
              <motion.circle
                cx="138"
                cy="74"
                r="10"
                fill="var(--accent-rose)"
                initial={{ scale: 0.9, opacity: 0.9 }}
                animate={
                  isActive
                    ? { scale: [0.85, 1.3, 0.85], opacity: [0.95, 0.45, 0.95] }
                    : { scale: 0.9, opacity: 0.9 }
                }
                transition={{ repeat: Infinity, duration: 1.5 }}
                style={{ transformOrigin: "138px 74px" }}
              />
              <circle cx="138" cy="74" r="5" fill="#ffffff" />
              <text
                x="138"
                y="102"
                textAnchor="middle"
                fill="var(--text)"
                fontSize="12"
                fontWeight="800"
              >
                RAMPUR CLUSTER
              </text>
            </svg>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "9px 12px",
              borderRadius: 10,
              background: isDark
                ? "rgba(244,63,94,0.12)"
                : "rgba(225,29,72,0.08)",
              fontSize: 12.5,
              fontWeight: 600,
              color: "var(--text)",
            }}
          >
            <AlertTriangle size={16} style={{ color: "var(--accent-rose)", flexShrink: 0 }} />
            <span>
              <strong>3 acute fever + rash cases</strong> detected in 48h — alerts
              PHC Medical Officer automatically.
            </span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
