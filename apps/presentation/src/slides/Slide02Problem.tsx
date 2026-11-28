import React from "react";
import { motion } from "framer-motion";
import {
  FileText,
  WifiOff,
  CalendarClock,
  AlertTriangle,
  Radio,
} from "lucide-react";
import type { SlideProps } from "../types";

const REALITY_CARDS = [
  {
    stat: "10+ Lakh",
    title: "ASHA Workers on Paper Registers",
    hindi: "आशा दीदी के भारी रजिस्टर",
    body: "Over 10 lakh frontline ASHA workers track pregnancies in handwritten books — slow to search, impossible to auto-alert a doctor when danger strikes.",
    tag: "Manual & Delayed",
    icon: FileText,
    accent: "var(--accent-saffron)",
  },
  {
    stat: "0 Bars",
    title: "Zero Signal Inside Rural Homes",
    hindi: "घर के अंदर नेटवर्क गायब",
    body: "Emergencies happen at 2 AM inside brick and mud-walled homes where 4G disappears. Cloud-only apps spin endlessly right when seconds matter.",
    tag: "Offline Dead Zones",
    icon: WifiOff,
    accent: "var(--accent-rose)",
  },
  {
    stat: "2–4 Wks",
    title: "Long Gaps for High-Risk Mothers",
    hindi: "जाँच के बीच लंबा अंतराल",
    body: "High-risk mothers and newborns often wait weeks between PHC visits — so early warning signs like bleeding, fever, or high BP go unnoticed.",
    tag: "Silent Risk Window",
    icon: CalendarClock,
    accent: "var(--accent-cyan)",
  },
];

export default function Slide02Problem({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";

  return (
    <div className="slide-frame" style={{ gap: 22 }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
        transition={{ duration: 0.55 }}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          gap: 24,
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
              color: "var(--accent-rose)",
              background: isDark
                ? "rgba(244, 63, 94, 0.14)"
                : "rgba(225, 29, 72, 0.1)",
              borderColor: isDark
                ? "rgba(244, 63, 94, 0.35)"
                : "rgba(225, 29, 72, 0.3)",
            }}
          >
            <AlertTriangle size={14} />
            <span>THE RURAL REALITY · ज़मीनी हकीकत</span>
          </span>
          <h2
            style={{
              fontSize: "clamp(2rem, 3.6vw, 3rem)",
              fontWeight: 800,
              margin: "12px 0 6px 0",
              letterSpacing: "-0.03em",
              color: "var(--text)",
              lineHeight: 1.12,
            }}
          >
            Healthcare Shouldn&apos;t Wait for a{" "}
            <span className="gradient-text">Mobile Signal</span>
          </h2>
          <p
            style={{
              margin: 0,
              fontSize: "1.02rem",
              color: "var(--text-muted)",
              maxWidth: 700,
              lineHeight: 1.5,
            }}
          >
            Every day across rural India, critical minutes are lost between a
            mother&apos;s home, her{" "}
            <strong style={{ color: "var(--text)" }}>आशा दीदी</strong>, and the{" "}
            <strong style={{ color: "var(--text)" }}>
              प्राथमिक स्वास्थ्य केन्द्र
            </strong>
            .
          </p>
        </div>

        {/* Animated Signal-Lost Indicator */}
        <motion.div
          className="glass-card"
          style={{
            padding: "12px 18px",
            borderRadius: 16,
            display: "flex",
            alignItems: "center",
            gap: 14,
            borderColor: isDark
              ? "rgba(244, 63, 94, 0.35)"
              : "rgba(225, 29, 72, 0.28)",
          }}
        >
          <div
            style={{
              position: "relative",
              width: 42,
              height: 42,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <motion.span
              animate={{ scale: [1, 1.7], opacity: [0.55, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
              style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                border: "2px solid var(--accent-rose)",
              }}
            />
            <WifiOff size={22} style={{ color: "var(--accent-rose)" }} />
          </div>
          <div>
            <div
              style={{
                fontSize: "0.78rem",
                fontWeight: 750,
                letterSpacing: "0.06em",
                color: "var(--accent-rose)",
              }}
            >
              SIGNAL LOST · 02:14 AM
            </div>
            <div style={{ fontSize: "0.84rem", color: "var(--text-muted)" }}>
              Cloud apps fail when needed most
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Animated Heartbeat -> Flatline Signal Bar */}
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, scaleX: 0.96 }}
        animate={isActive ? { opacity: 1, scaleX: 1 } : { opacity: 0.4, scaleX: 0.96 }}
        transition={{ duration: 0.6, delay: 0.12 }}
        style={{
          padding: "14px 22px",
          borderRadius: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 18,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Radio size={18} style={{ color: "var(--accent-saffron)" }} />
          <span style={{ fontSize: "0.9rem", fontWeight: 650, color: "var(--text)" }}>
            Emergency at Home
          </span>
        </div>

        <svg
          viewBox="0 0 640 42"
          style={{ flex: 1, height: 34, maxWidth: 640 }}
          aria-hidden="true"
        >
          {/* Active pulse on left, broken dashed gap in middle, waiting clinic on right */}
          <motion.path
            d="M 8 21 L 90 21 L 106 8 L 120 35 L 136 12 L 150 21 L 245 21"
            fill="none"
            stroke="var(--accent-rose)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={320}
            initial={{ strokeDashoffset: 320 }}
            animate={
              isActive ? { strokeDashoffset: 0 } : { strokeDashoffset: 320 }
            }
            transition={{ duration: 1.2, ease: "easeOut" }}
          />
          <line
            x1="265"
            y1="21"
            x2="455"
            y2="21"
            stroke="var(--text-muted)"
            strokeWidth="2"
            strokeDasharray="6 8"
            opacity={0.5}
          />
          <motion.circle
            cx="360"
            cy="21"
            r="6"
            fill="var(--accent-rose)"
            animate={{ opacity: [1, 0.2, 1], scale: [1, 1.3, 1] }}
            transition={{ duration: 1.4, repeat: Infinity }}
          />
          <line
            x1="475"
            y1="21"
            x2="632"
            y2="21"
            stroke="var(--accent-cyan)"
            strokeWidth="2.5"
            opacity={0.45}
          />
        </svg>

        <div
          style={{
            fontSize: "0.85rem",
            fontWeight: 650,
            color: "var(--text-muted)",
            whiteSpace: "nowrap",
          }}
        >
          PHC Doctor Unaware
        </div>
      </motion.div>

      {/* 3 Dramatic Story Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 20,
        }}
      >
        {REALITY_CARDS.map((card, i) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.title}
              className="glass-card"
              initial={{ opacity: 0, y: 28 }}
              animate={
                isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 16 }
              }
              transition={{
                duration: 0.6,
                delay: 0.18 + i * 0.12,
                ease: [0.22, 1, 0.36, 1],
              }}
              whileHover={{ y: -5 }}
              style={{
                padding: "24px 24px 22px",
                borderRadius: 20,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: 16,
                borderTop: `3px solid ${card.accent}`,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 13,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: isDark
                        ? "rgba(255,255,255,0.06)"
                        : "rgba(15,23,42,0.06)",
                      color: card.accent,
                    }}
                  >
                    <Icon size={22} />
                  </div>
                  <span
                    className="pill"
                    style={{
                      fontSize: "0.75rem",
                      fontWeight: 700,
                      padding: "4px 10px",
                      color: card.accent,
                    }}
                  >
                    {card.tag}
                  </span>
                </div>

                <div>
                  <div
                    className="metric-value"
                    style={{
                      fontSize: "clamp(2.1rem, 3.2vw, 2.75rem)",
                      fontWeight: 850,
                      letterSpacing: "-0.03em",
                      color: card.accent,
                      lineHeight: 1.05,
                    }}
                  >
                    {card.stat}
                  </div>
                  <h3
                    style={{
                      fontSize: "1.12rem",
                      fontWeight: 750,
                      color: "var(--text)",
                      margin: "10px 0 4px 0",
                      lineHeight: 1.25,
                    }}
                  >
                    {card.title}
                  </h3>
                  <div
                    style={{
                      fontSize: "0.84rem",
                      fontWeight: 600,
                      color: "var(--text-muted)",
                      opacity: 0.9,
                    }}
                  >
                    {card.hindi}
                  </div>
                </div>

                <p
                  style={{
                    margin: 0,
                    fontSize: "0.94rem",
                    lineHeight: 1.58,
                    color: "var(--text-muted)",
                  }}
                >
                  {card.body}
                </p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
