import { motion } from "framer-motion";
import {
  Languages,
  Watch,
  Smartphone,
  Check,
  X,
  Plane,
  Mic,
  Vibrate,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { SlideProps } from "../types";

const HINDI_TERMS = [
  { hi: "ज्वर", en: "Fever" },
  { hi: "श्वास कष्ट", en: "Breathlessness" },
  { hi: "आपातकाल", en: "Emergency" },
  { hi: "रक्तचाप", en: "Blood Pressure" },
];

export default function Slide09IndiaReady({ theme, isActive }: SlideProps) {
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
        initial={{ opacity: 0, y: -14 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: -14 }}
        transition={{ duration: 0.42 }}
        style={{ display: "flex", flexDirection: "column", gap: 8 }}
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
              color: "var(--accent-saffron)",
              borderColor: "var(--accent-saffron)",
            }}
          >
            <Sparkles size={13} />
            Field-Tested for India · Real Language &amp; Hardware
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
          Built for <span className="gradient-text">Real Bharat</span>
        </h1>

        <p
          style={{
            margin: 0,
            fontSize: "clamp(14px, 1.35vw, 17px)",
            color: "var(--text-muted)",
            maxWidth: 780,
          }}
        >
          Not a generic Western prototype — every word, tap, and hardware signal
          is crafted for rural ASHA Didis and village families.
        </p>
      </motion.div>

      {/* 3 Visual Feature Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 18,
          alignItems: "stretch",
        }}
      >
        {/* Card 1: Pure Shuddh Tatsama Hindi */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, y: 24 }}
          animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
          transition={{ delay: 0.14, type: "spring", stiffness: 170, damping: 20 }}
          style={{
            padding: "22px 20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 16,
            borderTop: "3px solid var(--accent-saffron)",
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
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  letterSpacing: "0.1em",
                  color: "var(--accent-saffron)",
                }}
              >
                01 · VERNACULAR DIGNITY
              </span>
              <Languages size={20} style={{ color: "var(--accent-saffron)" }} />
            </div>

            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text)" }}>
              Pure <em>Shuddh Tatsama</em> Hindi
            </div>

            {/* Devanagari chips */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 8,
              }}
            >
              {HINDI_TERMS.map((t, i) => (
                <motion.div
                  key={t.hi}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={
                    isActive
                      ? { opacity: 1, scale: 1 }
                      : { opacity: 0, scale: 0.9 }
                  }
                  transition={{ delay: 0.3 + i * 0.08 }}
                  style={{
                    padding: "9px 10px",
                    borderRadius: 10,
                    background: isDark
                      ? "rgba(245, 158, 11, 0.1)"
                      : "rgba(245, 158, 11, 0.12)",
                    border: "1px solid var(--surface-border)",
                  }}
                >
                  <div
                    style={{
                      fontSize: 17,
                      fontWeight: 800,
                      color: "var(--text)",
                    }}
                  >
                    {t.hi}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
                    {t.en}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              paddingTop: 12,
              borderTop: "1px solid var(--surface-border)",
              fontSize: 12.5,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                color: "var(--accent-emerald)",
                fontWeight: 700,
              }}
            >
              <Check size={15} /> Zero Hinglish or awkward translations
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                color: "var(--accent-rose)",
                fontWeight: 600,
              }}
            >
              <X size={15} /> Zero broken nukta / phonetic typos
            </div>
          </div>
        </motion.div>

        {/* Card 2: 2-Tap Family Watch & ₹0 Phone SOS Mode */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, y: 24 }}
          animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
          transition={{ delay: 0.26, type: "spring", stiffness: 170, damping: 20 }}
          style={{
            padding: "22px 20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 16,
            borderTop: "3px solid var(--accent-rose)",
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
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  letterSpacing: "0.1em",
                  color: "var(--accent-rose)",
                }}
              >
                02 · ZERO FALSE ALARMS
              </span>
              <Watch size={20} style={{ color: "var(--accent-rose)" }} />
            </div>

            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text)" }}>
              2-Tap Watch &amp; ₹0 Phone SOS
            </div>

            {/* Interactive-looking 2-Tap Visual */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 10,
                padding: "14px 12px",
                borderRadius: 12,
                background: isDark
                  ? "rgba(244, 63, 94, 0.09)"
                  : "rgba(225, 29, 72, 0.07)",
                border: "1px solid var(--surface-border)",
              }}
            >
              <div style={{ textAlign: "center", flex: 1 }}>
                <motion.div
                  animate={isActive ? { scale: [1, 1.07, 1] } : {}}
                  transition={{ repeat: Infinity, duration: 2.2 }}
                  style={{
                    width: 44,
                    height: 44,
                    margin: "0 auto 6px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 900,
                    fontSize: 14,
                    background: "var(--accent-saffron)",
                    color: "#090d16",
                  }}
                >
                  1
                </motion.div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>
                  Tap to Arm
                </div>
              </div>

              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: "var(--text-muted)",
                }}
              >
                2s window →
              </div>

              <div style={{ textAlign: "center", flex: 1 }}>
                <motion.div
                  animate={isActive ? { scale: [1, 1.1, 1] } : {}}
                  transition={{ repeat: Infinity, duration: 2.2, delay: 0.7 }}
                  style={{
                    width: 44,
                    height: 44,
                    margin: "0 auto 6px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 900,
                    fontSize: 14,
                    background: "var(--accent-rose)",
                    color: "#ffffff",
                  }}
                >
                  2
                </motion.div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>
                  Confirm SOS
                </div>
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
              Prevents accidental 108 ambulance false alarms from pocket bumps or
              curious toddlers.
            </p>
          </div>

          <div
            style={{
              paddingTop: 12,
              borderTop: "1px solid var(--surface-border)",
              fontSize: 12.5,
              fontWeight: 700,
              color: "var(--accent-emerald)",
            }}
          >
            Works on loaned watch OR any family phone (₹0 extra cost)
          </div>
        </motion.div>

        {/* Card 3: Native Signed Android APK */}
        <motion.div
          className="glass-card"
          initial={{ opacity: 0, y: 24 }}
          animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 24 }}
          transition={{ delay: 0.38, type: "spring", stiffness: 170, damping: 20 }}
          style={{
            padding: "22px 20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: 16,
            borderTop: "3px solid var(--accent-cyan)",
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
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 800,
                  letterSpacing: "0.1em",
                  color: "var(--accent-cyan)",
                }}
              >
                03 · REAL HARDWARE
              </span>
              <Smartphone size={20} style={{ color: "var(--accent-cyan)" }} />
            </div>

            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--text)" }}>
              Native Signed Android APK
            </div>

            <div
              style={{
                padding: "11px 12px",
                borderRadius: 11,
                background: isDark
                  ? "rgba(6, 182, 212, 0.1)"
                  : "rgba(6, 182, 212, 0.09)",
                border: "1px solid var(--surface-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 800, color: "var(--text)" }}>
                  Samsung Galaxy S23
                </div>
                <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
                  Verified on real device · Release build
                </div>
              </div>
              <ShieldCheck size={22} style={{ color: "var(--accent-emerald)" }} />
            </div>

            {/* Hardware Capability Pills */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { icon: Plane, text: "Full Airplane-Mode operation" },
                { icon: Mic, text: "Native hardware mic voice triage" },
                { icon: Vibrate, text: "Tactile haptic SOS confirmation" },
              ].map((feat) => {
                const FIcon = feat.icon;
                return (
                  <div
                    key={feat.text}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 9,
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--text)",
                    }}
                  >
                    <FIcon size={15} style={{ color: "var(--accent-cyan)" }} />
                    {feat.text}
                  </div>
                );
              })}
            </div>
          </div>

          <div
            style={{
              paddingTop: 12,
              borderTop: "1px solid var(--surface-border)",
              fontSize: 12.5,
              fontWeight: 700,
              color: "var(--accent-cyan)",
            }}
          >
            Sideloadable APK — zero Play Store or internet needed
          </div>
        </motion.div>
      </div>
    </div>
  );
}
