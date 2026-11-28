import React from "react";
import { motion } from "framer-motion";
import {
  WifiOff,
  ShieldCheck,
  Coins,
  HeartPulse,
  Watch,
  Smartphone,
  Laptop,
  Sparkles,
} from "lucide-react";
import type { SlideProps } from "../types";

const TRUST_BADGES = [
  {
    icon: WifiOff,
    label: "100% Airplane Mode",
    sub: "Works with zero signal",
    color: "var(--accent-saffron)",
  },
  {
    icon: ShieldCheck,
    label: "WHO Clinical Safety Floor",
    sub: "Deterministic, zero guesswork",
    color: "var(--accent-emerald)",
  },
  {
    icon: Coins,
    label: "Zero Cloud Cost",
    sub: "Runs on local rural hardware",
    color: "var(--accent-cyan)",
  },
];

export default function Slide01Hero({ theme, isActive }: SlideProps) {
  const isDark = theme === "dark";

  return (
    <div className="slide-frame">
      <div
        style={{
          width: "100%",
          display: "grid",
          gridTemplateColumns: "1.18fr 0.82fr",
          gap: 40,
          alignItems: "center",
        }}
      >
      {/* Left: Title, Subtitle & Trust Badges */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 12 }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
        style={{ display: "flex", flexDirection: "column", gap: 22 }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            className="pill"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "7px 14px",
              fontSize: "0.86rem",
              fontWeight: 600,
              letterSpacing: "0.02em",
              color: "var(--accent-saffron)",
              borderColor: isDark
                ? "rgba(245, 158, 11, 0.38)"
                : "rgba(217, 119, 6, 0.35)",
              background: isDark
                ? "rgba(245, 158, 11, 0.12)"
                : "rgba(245, 158, 11, 0.10)",
            }}
          >
            <Sparkles size={14} />
            <span>आरोग्य संजाल · Rural India&apos;s Offline Health Mesh</span>
          </span>
        </div>

        <div>
          <motion.h1
            className="gradient-text"
            initial={{ opacity: 0, y: 18 }}
            animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.5, y: 10 }}
            transition={{ duration: 0.7, delay: 0.08 }}
            style={{
              fontSize: "clamp(3.1rem, 5.2vw, 4.7rem)",
              fontWeight: 850,
              lineHeight: 1.04,
              letterSpacing: "-0.035em",
              margin: 0,
            }}
          >
            Aarogya Mesh
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 8 }}
            transition={{ duration: 0.65, delay: 0.18 }}
            style={{
              fontSize: "clamp(1.18rem, 1.8vw, 1.48rem)",
              fontWeight: 600,
              color: "var(--text)",
              margin: "14px 0 0 0",
              lineHeight: 1.38,
            }}
          >
            Offline-First Healthcare Mesh for Rural India
            <span
              style={{
                display: "block",
                marginTop: 6,
                fontSize: "1.02rem",
                fontWeight: 600,
                color: "var(--accent-cyan)",
                letterSpacing: "0.02em",
              }}
            >
              Watch · ASHA Phone · PHC Laptop
            </span>
          </motion.p>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={isActive ? { opacity: 1 } : { opacity: 0.4 }}
          transition={{ duration: 0.65, delay: 0.28 }}
          style={{
            fontSize: "1.03rem",
            lineHeight: 1.6,
            color: "var(--text-muted)",
            margin: 0,
            maxWidth: 580,
          }}
        >
          Instant, life-saving maternal &amp; newborn guidance for mothers,{" "}
          <strong style={{ color: "var(--text)", fontWeight: 650 }}>
            आशा दीदी
          </strong>
          , and{" "}
          <strong style={{ color: "var(--text)", fontWeight: 650 }}>
            प्राथमिक स्वास्थ्य केन्द्र
          </strong>{" "}
          doctors — built to work reliably even when the nearest mobile tower is
          kilometers away.
        </motion.p>

        {/* Trust Badges */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.4, y: 10 }}
          transition={{ duration: 0.65, delay: 0.36 }}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: 14,
            marginTop: 6,
          }}
        >
          {TRUST_BADGES.map((badge, idx) => {
            const Icon = badge.icon;
            return (
              <motion.div
                key={badge.label}
                className="glass-card"
                initial={{ opacity: 0, y: 16 }}
                animate={
                  isActive ? { opacity: 1, y: 0 } : { opacity: 0.5, y: 10 }
                }
                transition={{ duration: 0.5, delay: 0.38 + idx * 0.1 }}
                whileHover={{ y: -3 }}
                style={{
                  padding: "14px 14px",
                  borderRadius: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 10,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: isDark
                      ? "rgba(255,255,255,0.06)"
                      : "rgba(15,23,42,0.06)",
                    color: badge.color,
                  }}
                >
                  <Icon size={18} />
                </div>
                <div
                  style={{
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    color: "var(--text)",
                    lineHeight: 1.25,
                  }}
                >
                  {badge.label}
                </div>
                <div
                  style={{
                    fontSize: "0.78rem",
                    color: "var(--text-muted)",
                    lineHeight: 1.35,
                  }}
                >
                  {badge.sub}
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </motion.div>

      {/* Right: Animated 3-Ring Orbital Emblem */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={
          isActive ? { opacity: 1, scale: 1 } : { opacity: 0.4, scale: 0.94 }
        }
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 430,
        }}
      >
        <svg
          viewBox="0 0 420 420"
          style={{
            width: "100%",
            maxWidth: 420,
            height: "auto",
            overflow: "visible",
          }}
          aria-label="Aarogya Mesh 3-tier orbital emblem"
        >
          <defs>
            <radialGradient id="heroCoreGlow" cx="50%" cy="50%" r="50%">
              <stop
                offset="0%"
                stopColor="var(--accent-saffron)"
                stopOpacity={isDark ? 0.34 : 0.24}
              />
              <stop
                offset="55%"
                stopColor="var(--accent-emerald)"
                stopOpacity={isDark ? 0.14 : 0.1}
              />
              <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity={0} />
            </radialGradient>
            <linearGradient id="ringOuterGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent-cyan)" />
              <stop offset="100%" stopColor="var(--accent-emerald)" />
            </linearGradient>
            <linearGradient id="ringMidGrad" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="var(--accent-emerald)" />
              <stop offset="100%" stopColor="var(--accent-saffron)" />
            </linearGradient>
          </defs>

          {/* Soft glow aura */}
          <circle cx="210" cy="210" r="190" fill="url(#heroCoreGlow)" />

          {/* Outer Ring — Tier 2 PHC Laptop */}
          <motion.g
            animate={{ rotate: 360 }}
            transition={{ duration: 36, repeat: Infinity, ease: "linear" }}
            style={{ originX: "210px", originY: "210px" }}
          >
            <circle
              cx="210"
              cy="210"
              r="172"
              fill="none"
              stroke="url(#ringOuterGrad)"
              strokeWidth="2"
              strokeDasharray="10 10"
              opacity={isDark ? 0.65 : 0.72}
            />
            <circle cx="210" cy="38" r="6.5" fill="var(--accent-cyan)" />
            <circle
              cx="210"
              cy="38"
              r="12"
              fill="var(--accent-cyan)"
              opacity={0.22}
            />
          </motion.g>

          {/* Middle Ring — Tier 1 ASHA Phone */}
          <motion.g
            animate={{ rotate: -360 }}
            transition={{ duration: 24, repeat: Infinity, ease: "linear" }}
            style={{ originX: "210px", originY: "210px" }}
          >
            <circle
              cx="210"
              cy="210"
              r="124"
              fill="none"
              stroke="url(#ringMidGrad)"
              strokeWidth="2.4"
              strokeDasharray="16 8"
              opacity={isDark ? 0.82 : 0.85}
            />
            <circle cx="334" cy="210" r="6" fill="var(--accent-emerald)" />
            <circle
              cx="334"
              cy="210"
              r="12"
              fill="var(--accent-emerald)"
              opacity={0.22}
            />
          </motion.g>

          {/* Inner Ring — Tier 0 Watch */}
          <motion.g
            animate={{ rotate: 360 }}
            transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
            style={{ originX: "210px", originY: "210px" }}
          >
            <circle
              cx="210"
              cy="210"
              r="76"
              fill="none"
              stroke="var(--accent-saffron)"
              strokeWidth="2.4"
              opacity={0.9}
            />
            <circle cx="210" cy="286" r="5.5" fill="var(--accent-saffron)" />
          </motion.g>

          {/* Pulsing Core Circle */}
          <motion.circle
            cx="210"
            cy="210"
            r="46"
            fill={isDark ? "rgba(15, 23, 42, 0.88)" : "rgba(255, 255, 255, 0.94)"}
            stroke="var(--accent-saffron)"
            strokeWidth="2.5"
            animate={{ scale: [1, 1.06, 1] }}
            transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
            style={{ originX: "210px", originY: "210px" }}
          />
        </svg>

        {/* Center HeartPulse Icon */}
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
          style={{
            position: "absolute",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--accent-saffron)",
            pointerEvents: "none",
          }}
        >
          <HeartPulse size={34} strokeWidth={2.3} />
          <span
            style={{
              fontSize: "0.68rem",
              fontWeight: 700,
              letterSpacing: "0.08em",
              marginTop: 2,
              color: "var(--text)",
            }}
          >
            MESH
          </span>
        </motion.div>

        {/* Floating Tier Chips */}
        <motion.div
          className="glass-card"
          animate={{ y: [0, -5, 0] }}
          transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
          style={{
            position: "absolute",
            top: 14,
            right: 4,
            padding: "8px 13px",
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: "0.8rem",
            fontWeight: 650,
            color: "var(--text)",
          }}
        >
          <Laptop size={15} style={{ color: "var(--accent-cyan)" }} />
          <span>Tier 2 · PHC Laptop</span>
        </motion.div>

        <motion.div
          className="glass-card"
          animate={{ y: [0, 6, 0] }}
          transition={{
            duration: 4.8,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 0.6,
          }}
          style={{
            position: "absolute",
            bottom: 58,
            left: -6,
            padding: "8px 13px",
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: "0.8rem",
            fontWeight: 650,
            color: "var(--text)",
          }}
        >
          <Smartphone size={15} style={{ color: "var(--accent-emerald)" }} />
          <span>Tier 1 · ASHA Phone</span>
        </motion.div>

        <motion.div
          className="glass-card"
          animate={{ y: [0, -4, 0] }}
          transition={{
            duration: 3.8,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1.1,
          }}
          style={{
            position: "absolute",
            bottom: 10,
            right: 22,
            padding: "8px 13px",
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: "0.8rem",
            fontWeight: 650,
            color: "var(--text)",
          }}
        >
          <Watch size={15} style={{ color: "var(--accent-saffron)" }} />
          <span>Tier 0 · Mother&apos;s Watch</span>
        </motion.div>
      </motion.div>
      </div>
    </div>
  );
}
