import React from "react";
import { motion } from "framer-motion";
import {
  Watch,
  Smartphone,
  Laptop,
  CloudOff,
  ShieldCheck,
  Lock,
  HardDrive,
  ArrowRight,
  Ban,
  CheckCircle2,
} from "lucide-react";
import type { SlideProps } from "../types";

const TIERS = [
  {
    tier: "TIER 0",
    name: "Smart Watch",
    storage: "Local App Storage",
    detail: "Holds live SOS trigger & vital snapshot; clears cleanly after handoff.",
    badge: "On-Wrist Ring Buffer",
    icon: Watch,
    accent: "var(--accent-saffron)",
  },
  {
    tier: "TIER 1",
    name: "ASHA Phone APK",
    storage: "Private 127.0.0.1 Storage",
    detail: "Encrypted offline SQLite queue inside the signed Android APK. Zero remote URLs.",
    badge: "Airplane-Mode Queue",
    icon: Smartphone,
    accent: "var(--accent-cyan)",
  },
  {
    tier: "TIER 2",
    name: "PHC Clinic Laptop",
    storage: "phc_hub.db + .webm Folder",
    detail: "Single SQLite database & local voice audio folder owned 100% by the clinic.",
    badge: "Clinic Sovereign Store",
    icon: Laptop,
    accent: "var(--accent-emerald)",
  },
];

export default function Slide07Storage({ theme, isActive }: SlideProps) {
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
        gap: 22,
        padding: "16px 28px 68px",
        boxSizing: "border-box",
      }}
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -16 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: -16 }}
        transition={{ duration: 0.45 }}
        style={{ display: "flex", flexDirection: "column", gap: 8 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
            <Lock size={13} />
            Privacy by Architecture · DPDP Act 2023
          </span>
        </div>

        <h1
          style={{
            margin: 0,
            fontSize: "clamp(28px, 3.4vw, 44px)",
            fontWeight: 800,
            lineHeight: 1.12,
            letterSpacing: "-0.02em",
            color: "var(--text)",
          }}
        >
          Where Your Data Lives{" "}
          <span className="gradient-text">(100% Private, Zero Cloud)</span>
        </h1>

        <p
          style={{
            margin: 0,
            fontSize: "clamp(14px, 1.35vw, 17px)",
            color: "var(--text-muted)",
            maxWidth: 820,
            lineHeight: 1.45,
          }}
        >
          Every heartbeat, Hindi voice note, and triage score stays inside the
          village health chain — never sent to third-party servers.
        </p>
      </motion.div>

      {/* Main 3-Tier + Crossed-Out Cloud Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr auto 1fr 1.05fr",
          alignItems: "stretch",
          gap: 12,
        }}
      >
        {TIERS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <React.Fragment key={item.tier}>
              <motion.div
                className="glass-card"
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                animate={
                  isActive
                    ? { opacity: 1, y: 0, scale: 1 }
                    : { opacity: 0, y: 24, scale: 0.96 }
                }
                transition={{
                  delay: 0.12 + idx * 0.12,
                  type: "spring",
                  stiffness: 180,
                  damping: 20,
                }}
                style={{
                  padding: "20px 18px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: 14,
                  borderTop: `3px solid ${item.accent}`,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
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
                        letterSpacing: "0.1em",
                        color: item.accent,
                      }}
                    >
                      {item.tier}
                    </span>
                    <div
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: 11,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        background: isDark
                          ? "rgba(255,255,255,0.06)"
                          : "rgba(15,23,42,0.06)",
                        color: item.accent,
                      }}
                    >
                      <Icon size={20} />
                    </div>
                  </div>

                  <div>
                    <div
                      style={{
                        fontSize: 19,
                        fontWeight: 700,
                        color: "var(--text)",
                        marginBottom: 4,
                      }}
                    >
                      {item.name}
                    </div>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        fontFamily:
                          "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        color: item.accent,
                        padding: "5px 9px",
                        borderRadius: 8,
                        background: isDark
                          ? "rgba(255,255,255,0.05)"
                          : "rgba(15,23,42,0.05)",
                        display: "inline-block",
                      }}
                    >
                      {item.storage}
                    </div>
                  </div>

                  <p
                    style={{
                      margin: 0,
                      fontSize: 13.5,
                      lineHeight: 1.48,
                      color: "var(--text-muted)",
                    }}
                  >
                    {item.detail}
                  </p>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 12,
                    fontWeight: 600,
                    color: "var(--text)",
                    paddingTop: 10,
                    borderTop: "1px solid var(--surface-border)",
                  }}
                >
                  <HardDrive size={14} style={{ color: item.accent }} />
                  {item.badge}
                </div>
              </motion.div>

              {idx < TIERS.length - 1 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.6 }}
                  animate={
                    isActive
                      ? { opacity: 1, scale: 1 }
                      : { opacity: 0, scale: 0.6 }
                  }
                  transition={{ delay: 0.25 + idx * 0.12 }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--accent-cyan)",
                  }}
                >
                  <motion.div
                    animate={isActive ? { x: [0, 5, 0] } : {}}
                    transition={{
                      repeat: Infinity,
                      duration: 1.8,
                      ease: "easeInOut",
                      delay: idx * 0.4,
                    }}
                  >
                    <ArrowRight size={20} />
                  </motion.div>
                </motion.div>
              )}
            </React.Fragment>
          );
        })}

        {/* Crossed-Out Cloud Card */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, scale: 0.92, x: 20 }}
          animate={
            isActive
              ? { opacity: 1, scale: 1, x: 0 }
              : { opacity: 0, scale: 0.92, x: 20 }
          }
          transition={{
            delay: 0.48,
            type: "spring",
            stiffness: 170,
            damping: 18,
          }}
          style={{
            padding: "20px 18px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 12,
            border: "2px dashed var(--accent-rose)",
            background: isDark
              ? "rgba(244, 63, 94, 0.08)"
              : "rgba(225, 29, 72, 0.06)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          {/* Animated diagonal strike-through */}
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
              opacity: isDark ? 0.22 : 0.16,
            }}
          >
            <motion.line
              x1="6"
              y1="94"
              x2="94"
              y2="6"
              stroke="var(--accent-rose)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray="130"
              initial={{ strokeDashoffset: 130 }}
              animate={
                isActive ? { strokeDashoffset: 0 } : { strokeDashoffset: 130 }
              }
              transition={{ delay: 0.72, duration: 0.55, ease: "easeOut" }}
            />
          </svg>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              position: "relative",
              zIndex: 1,
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: 800,
                letterSpacing: "0.1em",
                color: "var(--accent-rose)",
              }}
            >
              EXTERNAL CLOUD
            </span>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 11,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: isDark
                  ? "rgba(244, 63, 94, 0.18)"
                  : "rgba(225, 29, 72, 0.12)",
                color: "var(--accent-rose)",
              }}
            >
              <CloudOff size={20} />
            </div>
          </div>

          <div style={{ position: "relative", zIndex: 1 }}>
            <div
              className="metric-value"
              style={{
                fontSize: "clamp(30px, 3vw, 40px)",
                fontWeight: 900,
                color: "var(--accent-rose)",
                lineHeight: 1.05,
              }}
            >
              0 Bytes
            </div>
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 700,
                color: "var(--text)",
                marginTop: 4,
              }}
            >
              Sent to Third-Party Clouds
            </div>
            <p
              style={{
                margin: "8px 0 0",
                fontSize: 13,
                lineHeight: 1.45,
                color: "var(--text-muted)",
              }}
            >
              No OpenAI, no AWS buckets, no API keys, no silent telemetry.
            </p>
          </div>

          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              fontWeight: 700,
              color: "var(--accent-rose)",
              position: "relative",
              zIndex: 1,
              paddingTop: 10,
              borderTop: "1px dashed var(--accent-rose)",
            }}
          >
            <Ban size={14} />
            Zero External Leakage
          </div>
        </motion.div>
      </div>

      {/* Bottom Sovereignty Strip */}
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, y: 18 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 18 }}
        transition={{ delay: 0.6, duration: 0.45 }}
        style={{
          padding: "16px 22px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          borderLeft: "4px solid var(--accent-emerald)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: isDark
                ? "rgba(16, 185, 129, 0.16)"
                : "rgba(16, 185, 129, 0.12)",
              color: "var(--accent-emerald)",
            }}
          >
            <ShieldCheck size={22} />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text)" }}>
              DPDP Act 2023 Sovereign by Design
            </div>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Patient voice notes and records remain physically inside the
              Primary Health Centre.
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
          {[
            "Single-file SQLite backup",
            "Local .webm voice audit",
            "100% Airplane-Mode safe",
          ].map((point) => (
            <div
              key={point}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 600,
                color: "var(--text)",
              }}
            >
              <CheckCircle2 size={15} style={{ color: "var(--accent-emerald)" }} />
              {point}
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
