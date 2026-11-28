import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Smartphone,
  Watch,
  GitMerge,
  RotateCcw,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type { SlideProps } from "../types";

export default function Slide06Sync({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";
  const [merged, setMerged] = useState(false);
  const [userInteracted, setUserInteracted] = useState(false);

  // Gentle auto-play demonstration when the slide becomes active
  useEffect(() => {
    if (!isActive) {
      setMerged(false);
      setUserInteracted(false);
      return;
    }
    if (userInteracted) return;

    const timer = window.setTimeout(() => {
      setMerged(true);
    }, 2400);

    return () => window.clearTimeout(timer);
  }, [isActive, userInteracted]);

  const handleToggleMerge = () => {
    setUserInteracted(true);
    setMerged((prev) => !prev);
  };

  return (
    <div className="slide-frame" style={{ gap: 20 }}>
      {/* Header + Action Button */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
        transition={{ duration: 0.55 }}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          gap: 20,
          flexWrap: "wrap",
        }}
      >
        <div>
          <span
            className="pill"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 14px",
              fontSize: "0.82rem",
              fontWeight: 700,
              color: "var(--accent-cyan)",
              background: isDark
                ? "rgba(6, 182, 212, 0.14)"
                : "rgba(8, 145, 178, 0.1)",
            }}
          >
            <GitMerge size={14} />
            <span>SMART SYNC WITHOUT INTERNET · INTERACTIVE DEMO</span>
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
            Two Offline Edits. Same Second.{" "}
            <span className="gradient-text">Zero Data Lost.</span>
          </h2>
          <p
            style={{
              margin: 0,
              fontSize: "0.98rem",
              color: "var(--text-muted)",
              maxWidth: 680,
            }}
          >
            Normal apps overwrite one edit and silently erase the other. Aarogya
            Mesh merges every field cleanly the moment devices reconnect.
          </p>
        </div>

        {/* Interactive Simulate Merge Button */}
        <motion.button
          type="button"
          onClick={handleToggleMerge}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
          style={{
            cursor: "pointer",
            border: "none",
            borderRadius: 14,
            padding: "13px 22px",
            fontSize: "0.95rem",
            fontWeight: 750,
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            color: "#FFFFFF",
            background: merged
              ? "linear-gradient(135deg, #0EA5E9, #10B981)"
              : "linear-gradient(135deg, #F59E0B, #EC4899)",
            boxShadow: isDark
              ? "0 10px 28px -6px rgba(245, 158, 11, 0.45)"
              : "0 10px 24px -6px rgba(217, 119, 6, 0.35)",
          }}
        >
          {merged ? <RotateCcw size={18} /> : <GitMerge size={18} />}
          <span>{merged ? "Reset & Replay" : "Simulate Merge"}</span>
        </motion.button>
      </motion.div>

      {/* Interactive Stage */}
      <div
        className="glass-card"
        style={{
          padding: "26px 26px",
          borderRadius: 24,
          minHeight: 350,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <AnimatePresence mode="wait">
          {!merged ? (
            <motion.div
              key="split"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.92 }}
              transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto 1fr",
                gap: 22,
                alignItems: "center",
              }}
            >
              {/* Left Card: Phone Offline Edit */}
              <motion.div
                layoutId="sync-card-left"
                className="glass-card"
                style={{
                  padding: "22px 22px",
                  borderRadius: 20,
                  borderTop: "3px solid var(--accent-emerald)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
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
                    <Smartphone size={20} style={{ color: "var(--accent-emerald)" }} />
                    <span
                      style={{
                        fontSize: "1.02rem",
                        fontWeight: 800,
                        color: "var(--text)",
                      }}
                    >
                      ASHA Phone (Offline)
                    </span>
                  </div>
                  <span
                    className="pill"
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 700,
                      padding: "4px 10px",
                      color: "var(--accent-emerald)",
                    }}
                  >
                    10:14:02 AM
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--text-muted)",
                    fontWeight: 600,
                  }}
                >
                  Patient: <strong style={{ color: "var(--text)" }}>Sunita Devi (#SM-204)</strong>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <div
                    style={{
                      padding: "10px 13px",
                      borderRadius: 11,
                      background: isDark
                        ? "rgba(16, 185, 129, 0.14)"
                        : "rgba(5, 150, 105, 0.1)",
                      fontSize: "0.92rem",
                      fontWeight: 700,
                      color: "var(--text)",
                    }}
                  >
                    + Gestation Updated: Week 30
                  </div>
                  <div
                    style={{
                      padding: "10px 13px",
                      borderRadius: 11,
                      background: isDark
                        ? "rgba(16, 185, 129, 0.14)"
                        : "rgba(5, 150, 105, 0.1)",
                      fontSize: "0.92rem",
                      fontWeight: 700,
                      color: "var(--text)",
                    }}
                  >
                    + ANC Visit 3 Completed · BP 142/94
                  </div>
                </div>
              </motion.div>

              {/* Center Collision Indicator */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <motion.div
                  animate={{ scale: [1, 1.12, 1] }}
                  transition={{ duration: 1.8, repeat: Infinity }}
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isDark
                      ? "rgba(245, 158, 11, 0.18)"
                      : "rgba(217, 119, 6, 0.14)",
                    border: "2px solid var(--accent-saffron)",
                    color: "var(--accent-saffron)",
                  }}
                >
                  <Clock size={24} />
                </motion.div>
                <span
                  style={{
                    fontSize: "0.76rem",
                    fontWeight: 800,
                    color: "var(--accent-saffron)",
                    textAlign: "center",
                    letterSpacing: "0.04em",
                  }}
                >
                  SAME SECOND
                  <br />
                  OFFLINE EDIT
                </span>
              </div>

              {/* Right Card: Watch Offline Edit */}
              <motion.div
                layoutId="sync-card-right"
                className="glass-card"
                style={{
                  padding: "22px 22px",
                  borderRadius: 20,
                  borderTop: "3px solid var(--accent-rose)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
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
                    <Watch size={20} style={{ color: "var(--accent-rose)" }} />
                    <span
                      style={{
                        fontSize: "1.02rem",
                        fontWeight: 800,
                        color: "var(--text)",
                      }}
                    >
                      Mother&apos;s Watch (Offline)
                    </span>
                  </div>
                  <span
                    className="pill"
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 700,
                      padding: "4px 10px",
                      color: "var(--accent-rose)",
                    }}
                  >
                    10:14:02 AM
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--text-muted)",
                    fontWeight: 600,
                  }}
                >
                  Patient: <strong style={{ color: "var(--text)" }}>Sunita Devi (#SM-204)</strong>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <div
                    style={{
                      padding: "10px 13px",
                      borderRadius: 11,
                      background: isDark
                        ? "rgba(244, 63, 94, 0.16)"
                        : "rgba(225, 29, 72, 0.1)",
                      fontSize: "0.92rem",
                      fontWeight: 750,
                      color: "var(--text)",
                    }}
                  >
                    ! Emergency Bleeding SOS Tapped
                  </div>
                  <div
                    style={{
                      padding: "10px 13px",
                      borderRadius: 11,
                      background: isDark
                        ? "rgba(244, 63, 94, 0.16)"
                        : "rgba(225, 29, 72, 0.1)",
                      fontSize: "0.92rem",
                      fontWeight: 750,
                      color: "var(--accent-rose)",
                    }}
                  >
                    ! Severity Flag: RED EMERGENCY
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="merged"
              initial={{ opacity: 0, scale: 0.9, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              style={{
                maxWidth: 880,
                width: "100%",
                margin: "0 auto",
                padding: "24px 26px",
                borderRadius: 22,
                background: isDark
                  ? "linear-gradient(135deg, rgba(16,185,129,0.14), rgba(6,182,212,0.12))"
                  : "linear-gradient(135deg, rgba(5,150,105,0.09), rgba(8,145,178,0.08))",
                border: "2px solid var(--accent-emerald)",
                display: "flex",
                flexDirection: "column",
                gap: 18,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 13,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: "var(--accent-emerald)",
                      color: "#FFFFFF",
                    }}
                  >
                    <CheckCircle2 size={24} />
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: "0.76rem",
                        fontWeight: 800,
                        letterSpacing: "0.06em",
                        color: "var(--accent-emerald)",
                      }}
                    >
                      AUTOMATIC CONFLICT-FREE MERGE COMPLETE
                    </div>
                    <div
                      style={{
                        fontSize: "1.22rem",
                        fontWeight: 800,
                        color: "var(--text)",
                      }}
                    >
                      Unified Patient Record · Sunita Devi (#SM-204)
                    </div>
                  </div>
                </div>

                <span
                  className="pill"
                  style={{
                    padding: "7px 14px",
                    fontSize: "0.84rem",
                    fontWeight: 800,
                    color: "var(--accent-emerald)",
                    borderColor: "var(--accent-emerald)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <Sparkles size={14} />
                  0 Data Lost
                </span>
              </div>

              {/* Merged Fields Grid */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: 12,
                }}
              >
                <div
                  className="glass-card"
                  style={{
                    padding: "13px 16px",
                    borderRadius: 14,
                    borderLeft: "3px solid var(--accent-emerald)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 750,
                      color: "var(--accent-emerald)",
                      marginBottom: 4,
                    }}
                  >
                    PRESERVED FROM ASHA PHONE
                  </div>
                  <div
                    style={{
                      fontSize: "0.96rem",
                      fontWeight: 700,
                      color: "var(--text)",
                    }}
                  >
                    Week 30 · ANC Visit 3 Completed · BP 142/94
                  </div>
                </div>

                <div
                  className="glass-card"
                  style={{
                    padding: "13px 16px",
                    borderRadius: 14,
                    borderLeft: "3px solid var(--accent-rose)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 750,
                      color: "var(--accent-rose)",
                      marginBottom: 4,
                    }}
                  >
                    PRESERVED FROM MOTHER&apos;S WATCH
                  </div>
                  <div
                    style={{
                      fontSize: "0.96rem",
                      fontWeight: 750,
                      color: "var(--text)",
                      display: "flex",
                      alignItems: "center",
                      gap: 7,
                    }}
                  >
                    <ShieldAlert size={16} style={{ color: "var(--accent-rose)" }} />
                    Emergency Bleeding SOS · RED Priority
                  </div>
                </div>
              </div>

              <div
                style={{
                  fontSize: "0.88rem",
                  color: "var(--text-muted)",
                  display: "flex",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: 10,
                }}
              >
                <span>
                  Every edit is merged field-by-field — emergencies always rise
                  to the top.
                </span>
                <strong style={{ color: "var(--text)" }}>
                  Synced identically on Watch, Phone &amp; PHC Laptop
                </strong>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
