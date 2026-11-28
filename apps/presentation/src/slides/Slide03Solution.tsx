import React from "react";
import { motion } from "framer-motion";
import {
  Watch,
  Smartphone,
  Laptop,
  Zap,
  Wifi,
  CheckCircle2,
  Layers,
} from "lucide-react";
import type { SlideProps } from "../types";

const QUICK_POINTS = [
  {
    num: "01",
    title: "2-Tap SOS at Home",
    desc: "Mother taps a simple wristband during an emergency — instant offline alert with zero typing.",
    color: "var(--accent-saffron)",
  },
  {
    num: "02",
    title: "WHO + Hindi AI on Phone",
    desc: "आशा दीदी's Android phone triages danger signs and transcribes Hindi voice notes in Airplane Mode.",
    color: "var(--accent-emerald)",
  },
  {
    num: "03",
    title: "Auto-Sync at the PHC",
    desc: "Walking near the clinic Wi-Fi automatically syncs every patient record to the doctor's laptop.",
    color: "var(--accent-cyan)",
  },
];

export default function Slide03Solution({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";
  const nodeFill = isDark ? "rgba(15, 23, 42, 0.85)" : "rgba(255, 255, 255, 0.92)";
  const trackStroke = isDark ? "rgba(148, 163, 184, 0.25)" : "rgba(15, 23, 42, 0.16)";

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
          <Layers size={14} />
          <span>WHAT AAROGYA MESH DOES · IN 10 SECONDS</span>
        </span>
        <h2
          style={{
            fontSize: "clamp(2rem, 3.5vw, 2.9rem)",
            fontWeight: 800,
            margin: "10px 0 4px 0",
            letterSpacing: "-0.03em",
            color: "var(--text)",
            lineHeight: 1.12,
          }}
        >
          Three Everyday Devices.{" "}
          <span className="gradient-text">One Self-Healing Mesh.</span>
        </h2>
      </motion.div>

      {/* 3 Simple Bullets */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 16,
        }}
      >
        {QUICK_POINTS.map((pt, idx) => (
          <motion.div
            key={pt.num}
            className="glass-card"
            initial={{ opacity: 0, y: 18 }}
            animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
            transition={{ duration: 0.5, delay: 0.1 + idx * 0.1 }}
            style={{
              padding: "16px 18px",
              borderRadius: 16,
              display: "flex",
              gap: 14,
              alignItems: "flex-start",
            }}
          >
            <div
              style={{
                fontSize: "0.85rem",
                fontWeight: 800,
                color: pt.color,
                padding: "5px 9px",
                borderRadius: 9,
                background: isDark
                  ? "rgba(255,255,255,0.06)"
                  : "rgba(15,23,42,0.06)",
                flexShrink: 0,
              }}
            >
              {pt.num}
            </div>
            <div>
              <div
                style={{
                  fontSize: "1rem",
                  fontWeight: 750,
                  color: "var(--text)",
                  marginBottom: 4,
                }}
              >
                {pt.title}
              </div>
              <div
                style={{
                  fontSize: "0.87rem",
                  lineHeight: 1.48,
                  color: "var(--text-muted)",
                }}
              >
                {pt.desc}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Animated 3-Tier Architecture SVG */}
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, y: 22 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 12 }}
        transition={{ duration: 0.65, delay: 0.25 }}
        style={{
          padding: "22px 24px 18px",
          borderRadius: 22,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 10,
          }}
        >
          <span
            style={{
              fontSize: "0.85rem",
              fontWeight: 750,
              letterSpacing: "0.05em",
              color: "var(--text-muted)",
            }}
          >
            LIVE 3-TIER OFFLINE DATA FLOW
          </span>
          <div style={{ display: "flex", gap: 14, fontSize: "0.8rem", color: "var(--text-muted)" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Zap size={13} style={{ color: "var(--accent-saffron)" }} />
              Instant Local Hop
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <Wifi size={13} style={{ color: "var(--accent-cyan)" }} />
              Opportunistic Clinic Sync
            </span>
          </div>
        </div>

        <svg
          viewBox="0 0 1060 250"
          style={{ width: "100%", height: "auto", maxHeight: 255, overflow: "visible" }}
          aria-label="3-tier architecture from Watch 256MB to Phone 4GB to PHC Laptop 16GB"
        >
          <defs>
            <linearGradient id="link1Grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--accent-saffron)" />
              <stop offset="100%" stopColor="var(--accent-emerald)" />
            </linearGradient>
            <linearGradient id="link2Grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="var(--accent-emerald)" />
              <stop offset="100%" stopColor="var(--accent-cyan)" />
            </linearGradient>
          </defs>

          {/* Track 1: Watch -> Phone */}
          <line
            x1="280"
            y1="115"
            x2="400"
            y2="115"
            stroke={trackStroke}
            strokeWidth="4"
            strokeLinecap="round"
          />
          <line
            x1="280"
            y1="115"
            x2="400"
            y2="115"
            stroke="url(#link1Grad)"
            strokeWidth="2.5"
            strokeDasharray="6 6"
          />
          {/* Animated Packet 1 */}
          <motion.circle
            cx={286}
            cy={115}
            r={7}
            fill="var(--accent-saffron)"
            initial={{ x: 0, opacity: 0.2 }}
            animate={{ x: [0, 108], opacity: [0.2, 1, 1, 0.2] }}
            transition={{ duration: 2.1, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.circle
            cx={286}
            cy={115}
            r={13}
            fill="var(--accent-saffron)"
            initial={{ x: 0, opacity: 0 }}
            animate={{ x: [0, 108], opacity: [0, 0.28, 0] }}
            transition={{ duration: 2.1, repeat: Infinity, ease: "easeInOut" }}
          />
          <text
            x="340"
            y="92"
            textAnchor="middle"
            fill="var(--text-muted)"
            fontSize="12"
            fontWeight="650"
          >
            SOS &amp; Vitals
          </text>
          <text
            x="340"
            y="142"
            textAnchor="middle"
            fill="var(--accent-saffron)"
            fontSize="11"
            fontWeight="700"
          >
            0 ms · Offline
          </text>

          {/* Track 2: Phone -> PHC Laptop */}
          <line
            x1="660"
            y1="115"
            x2="780"
            y2="115"
            stroke={trackStroke}
            strokeWidth="4"
            strokeLinecap="round"
          />
          <line
            x1="660"
            y1="115"
            x2="780"
            y2="115"
            stroke="url(#link2Grad)"
            strokeWidth="2.5"
            strokeDasharray="6 6"
          />
          {/* Animated Packet 2 */}
          <motion.circle
            cx={666}
            cy={115}
            r={7}
            fill="var(--accent-cyan)"
            initial={{ x: 0, opacity: 0.2 }}
            animate={{ x: [0, 108], opacity: [0.2, 1, 1, 0.2] }}
            transition={{
              duration: 2.1,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.7,
            }}
          />
          <motion.circle
            cx={666}
            cy={115}
            r={13}
            fill="var(--accent-cyan)"
            initial={{ x: 0, opacity: 0 }}
            animate={{ x: [0, 108], opacity: [0, 0.28, 0] }}
            transition={{
              duration: 2.1,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.7,
            }}
          />
          <text
            x="720"
            y="92"
            textAnchor="middle"
            fill="var(--text-muted)"
            fontSize="12"
            fontWeight="650"
          >
            Smart Sync
          </text>
          <text
            x="720"
            y="142"
            textAnchor="middle"
            fill="var(--accent-cyan)"
            fontSize="11"
            fontWeight="700"
          >
            Zero Data Lost
          </text>

          {/* Node 0: Watch */}
          <g transform="translate(20, 22)">
            <rect
              width="260"
              height="186"
              rx="20"
              fill={nodeFill}
              stroke="var(--accent-saffron)"
              strokeWidth="2.2"
            />
            <rect
              x="18"
              y="18"
              width="86"
              height="24"
              rx="12"
              fill={isDark ? "rgba(245,158,11,0.18)" : "rgba(245,158,11,0.14)"}
            />
            <text
              x="61"
              y="34"
              textAnchor="middle"
              fill="var(--accent-saffron)"
              fontSize="11"
              fontWeight="800"
            >
              TIER 0 · HOME
            </text>
            <text
              x="18"
              y="76"
              fill="var(--text)"
              fontSize="20"
              fontWeight="800"
            >
              Mother&apos;s Watch
            </text>
            <text
              x="18"
              y="102"
              fill="var(--accent-saffron)"
              fontSize="13.5"
              fontWeight="750"
            >
              256 MB RAM · Loaned Band
            </text>
            <text
              x="18"
              y="134"
              fill="var(--text-muted)"
              fontSize="13"
            >
              • 2-Tap Emergency SOS
            </text>
            <text
              x="18"
              y="158"
              fill="var(--text-muted)"
              fontSize="13"
            >
              • Hindi Voice &amp; Heart-Rate Cue
            </text>
          </g>

          {/* Node 1: ASHA Phone */}
          <g transform="translate(400, 22)">
            <rect
              width="260"
              height="186"
              rx="20"
              fill={nodeFill}
              stroke="var(--accent-emerald)"
              strokeWidth="2.2"
            />
            <rect
              x="18"
              y="18"
              width="98"
              height="24"
              rx="12"
              fill={isDark ? "rgba(16,185,129,0.18)" : "rgba(5,150,105,0.14)"}
            />
            <text
              x="67"
              y="34"
              textAnchor="middle"
              fill="var(--accent-emerald)"
              fontSize="11"
              fontWeight="800"
            >
              TIER 1 · FIELD
            </text>
            <text
              x="18"
              y="76"
              fill="var(--text)"
              fontSize="20"
              fontWeight="800"
            >
              ASHA Phone
            </text>
            <text
              x="18"
              y="102"
              fill="var(--accent-emerald)"
              fontSize="13.5"
              fontWeight="750"
            >
              4 GB RAM · Everyday Android
            </text>
            <text
              x="18"
              y="134"
              fill="var(--text-muted)"
              fontSize="13"
            >
              • WHO IMNCI Safety Floor
            </text>
            <text
              x="18"
              y="158"
              fill="var(--text-muted)"
              fontSize="13"
            >
              • Offline Hindi Voice + AI Risk
            </text>
          </g>

          {/* Node 2: PHC Laptop */}
          <g transform="translate(780, 22)">
            <rect
              width="260"
              height="186"
              rx="20"
              fill={nodeFill}
              stroke="var(--accent-cyan)"
              strokeWidth="2.2"
            />
            <rect
              x="18"
              y="18"
              width="102"
              height="24"
              rx="12"
              fill={isDark ? "rgba(6,182,212,0.18)" : "rgba(8,145,178,0.14)"}
            />
            <text
              x="69"
              y="34"
              textAnchor="middle"
              fill="var(--accent-cyan)"
              fontSize="11"
              fontWeight="800"
            >
              TIER 2 · CLINIC
            </text>
            <text
              x="18"
              y="76"
              fill="var(--text)"
              fontSize="20"
              fontWeight="800"
            >
              PHC Laptop
            </text>
            <text
              x="18"
              y="102"
              fill="var(--accent-cyan)"
              fontSize="13.5"
              fontWeight="750"
            >
              16 GB RAM · Clinic Hub
            </text>
            <text
              x="18"
              y="134"
              fill="var(--text-muted)"
              fontSize="13"
            >
              • Red-First Doctor Triage Board
            </text>
            <text
              x="18"
              y="158"
              fill="var(--text-muted)"
              fontSize="13"
            >
              • Outbreak Radar &amp; 108 Dispatch
            </text>
          </g>
        </svg>

        {/* Bottom Hardware Strip */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 12,
            paddingTop: 10,
            borderTop: "1px solid var(--surface-border)",
            fontSize: "0.84rem",
            color: "var(--text-muted)",
          }}
        >
          <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
            <Watch size={15} style={{ color: "var(--accent-saffron)" }} />
            <strong style={{ color: "var(--text)" }}>Watch:</strong> 256 MB
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
            <Smartphone size={15} style={{ color: "var(--accent-emerald)" }} />
            <strong style={{ color: "var(--text)" }}>Phone:</strong> 4 GB
          </span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
            <Laptop size={15} style={{ color: "var(--accent-cyan)" }} />
            <strong style={{ color: "var(--text)" }}>PHC Hub:</strong> 16 GB
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 7,
              color: "var(--accent-emerald)",
              fontWeight: 700,
            }}
          >
            <CheckCircle2 size={15} />
            Zero Cloud Servers Required
          </span>
        </div>
      </motion.div>
    </div>
  );
}
