import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  BellRing,
  Mic,
  RefreshCw,
  Ambulance,
  ArrowRight,
  HeartHandshake,
  MapPin,
} from "lucide-react";
import type { SlideProps } from "../types";

const STORY_STEPS = [
  {
    step: "01",
    place: "Sunita's Home · Offline",
    title: "2-Tap SOS at Home",
    desc: "At Week 30, Sunita feels sudden bleeding and dizziness. She taps SOS twice on her wristband — instant alert, zero internet.",
    badge: "0 ms · No Signal",
    detail:
      "Haptic pulse confirms SOS is logged locally and queued for आशा दीदी's phone.",
    icon: BellRing,
    accent: "var(--accent-saffron)",
  },
  {
    step: "02",
    place: "आशा दीदी Arrives",
    title: "WHO Check + Hindi Voice",
    desc: "ASHA runs the 30-second WHO danger-sign checklist and speaks a Hindi voice note in Airplane Mode. Phone flags RED immediately.",
    badge: "100% Airplane Mode",
    detail:
      "Local AI extracts symptoms from Hindi speech while WHO rules lock RED priority.",
    icon: Mic,
    accent: "var(--accent-emerald)",
  },
  {
    step: "03",
    place: "PHC Hotspot Zone",
    title: "Auto-Sync at Clinic",
    desc: "The moment ASHA's phone enters the प्राथमिक स्वास्थ्य केन्द्र Wi-Fi range, Sunita's full case, vitals, and note sync automatically.",
    badge: "Zero-Touch Sync",
    detail:
      "Smart conflict-free sync guarantees Baby Aarav's & Sunita's records never overwrite.",
    icon: RefreshCw,
    accent: "var(--accent-cyan)",
  },
  {
    step: "04",
    place: "PHC Doctor Desk",
    title: "Risk Card -> 108 Ambulance",
    desc: "The doctor sees Sunita pinned at the top in RED with clear symptoms & vital bars — and dispatches a 108 ambulance right away.",
    badge: "108 Dispatched",
    detail:
      "No digging through paper registers — every critical clue is ready in one glance.",
    icon: Ambulance,
    accent: "var(--accent-rose)",
  },
];

export default function Slide04Story({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";
  const [selected, setSelected] = useState<number>(0);

  return (
    <div className="slide-frame" style={{ gap: 20 }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
        transition={{ duration: 0.55 }}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          flexWrap: "wrap",
          gap: 16,
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
              color: "var(--accent-saffron)",
              background: isDark
                ? "rgba(245, 158, 11, 0.14)"
                : "rgba(217, 119, 6, 0.1)",
            }}
          >
            <HeartHandshake size={14} />
            <span>A REAL VILLAGE STORY · सुनीता देवी और बेबी आरव</span>
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
            Sunita Devi &amp; Baby Aarav:{" "}
            <span className="gradient-text">SOS to 108 in Minutes</span>
          </h2>
        </div>

        <div
          className="glass-card"
          style={{
            padding: "10px 16px",
            borderRadius: 14,
            display: "flex",
            alignItems: "center",
            gap: 9,
            fontSize: "0.85rem",
            color: "var(--text-muted)",
          }}
        >
          <MapPin size={16} style={{ color: "var(--accent-emerald)" }} />
          <span>
            Rampur Village <strong style={{ color: "var(--text)" }}>-&gt;</strong>{" "}
            Block PHC (14 km away)
          </span>
        </div>
      </motion.div>

      {/* 4-Step Journey Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: 16,
          position: "relative",
        }}
      >
        {STORY_STEPS.map((item, idx) => {
          const Icon = item.icon;
          const activeCard = selected === idx;
          return (
            <motion.button
              key={item.step}
              type="button"
              onClick={() => setSelected(idx)}
              className="glass-card"
              initial={{ opacity: 0, y: 26 }}
              animate={
                isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 14 }
              }
              transition={{
                duration: 0.55,
                delay: 0.12 + idx * 0.11,
                ease: [0.22, 1, 0.36, 1],
              }}
              whileHover={{ y: -4 }}
              style={{
                textAlign: "left",
                cursor: "pointer",
                padding: "20px 18px",
                borderRadius: 20,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: 14,
                position: "relative",
                borderColor: activeCard
                  ? item.accent
                  : "var(--surface-border)",
                boxShadow: activeCard
                  ? isDark
                    ? `0 0 0 1px ${item.accent}, 0 14px 30px -10px rgba(0,0,0,0.5)`
                    : `0 0 0 1.5px ${item.accent}, 0 12px 24px -10px rgba(15,23,42,0.16)`
                  : undefined,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div
                    style={{
                      width: 42,
                      height: 42,
                      borderRadius: 12,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      background: isDark
                        ? "rgba(255,255,255,0.07)"
                        : "rgba(15,23,42,0.06)",
                      color: item.accent,
                    }}
                  >
                    <Icon size={21} />
                  </div>
                  <span
                    style={{
                      fontSize: "1.35rem",
                      fontWeight: 850,
                      color: item.accent,
                      opacity: activeCard ? 1 : 0.65,
                    }}
                  >
                    {item.step}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: "0.76rem",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: item.accent,
                  }}
                >
                  {item.place}
                </div>

                <h3
                  style={{
                    margin: 0,
                    fontSize: "1.08rem",
                    fontWeight: 780,
                    color: "var(--text)",
                    lineHeight: 1.25,
                  }}
                >
                  {item.title}
                </h3>

                <p
                  style={{
                    margin: 0,
                    fontSize: "0.88rem",
                    lineHeight: 1.52,
                    color: "var(--text-muted)",
                  }}
                >
                  {item.desc}
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingTop: 10,
                  borderTop: "1px solid var(--surface-border)",
                }}
              >
                <span
                  className="pill"
                  style={{
                    fontSize: "0.74rem",
                    fontWeight: 750,
                    padding: "4px 10px",
                    color: item.accent,
                  }}
                >
                  {item.badge}
                </span>
                {idx < STORY_STEPS.length - 1 && (
                  <ArrowRight
                    size={15}
                    style={{ color: "var(--text-muted)", opacity: 0.7 }}
                  />
                )}
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Interactive Spotlight Footer */}
      <motion.div
        key={selected}
        className="glass-card"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        style={{
          padding: "16px 22px",
          borderRadius: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 18,
          borderLeft: `4px solid ${STORY_STEPS[selected].accent}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span
            style={{
              fontSize: "0.8rem",
              fontWeight: 800,
              color: STORY_STEPS[selected].accent,
              letterSpacing: "0.05em",
              whiteSpace: "nowrap",
            }}
          >
            STEP {STORY_STEPS[selected].step} INSIGHT
          </span>
          <span
            style={{
              fontSize: "0.95rem",
              color: "var(--text)",
              fontWeight: 550,
            }}
          >
            {STORY_STEPS[selected].detail}
          </span>
        </div>

        <span
          style={{
            fontSize: "0.78rem",
            color: "var(--text-muted)",
            whiteSpace: "nowrap",
          }}
        >
          Click any step to inspect
        </span>
      </motion.div>
    </div>
  );
}
