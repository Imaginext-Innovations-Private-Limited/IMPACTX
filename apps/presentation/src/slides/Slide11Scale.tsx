import { motion } from "framer-motion";
import {
  Watch,
  Smartphone,
  Building2,
  RotateCw,
  IndianRupee,
  ArrowRight,
  CheckCircle2,
  Globe,
} from "lucide-react";
import type { SlideProps } from "../types";

export default function Slide11Scale({ theme, isActive }: SlideProps) {
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
            <IndianRupee size={13} />
            Rural Economics · NHM &amp; ABDM Ready
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
          Affordable at National Scale{" "}
          <span className="gradient-text">(NHM &amp; ABDM Ready)</span>
        </h1>

        <p
          style={{
            margin: 0,
            fontSize: "clamp(14px, 1.35vw, 17px)",
            color: "var(--text-muted)",
            maxWidth: 820,
          }}
        >
          Zero monthly cloud bills — built around rotating clinic hardware,
          existing family phones, and India&apos;s national digital health rails.
        </p>
      </motion.div>

      {/* 3-Stage Economics Flow */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr auto 1fr",
          alignItems: "stretch",
          gap: 14,
        }}
      >
        {/* Stage 1: Loaned ₹1,500 Wristband */}
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
            gap: 14,
            borderTop: "3px solid var(--accent-saffron)",
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
                  color: "var(--accent-saffron)",
                }}
              >
                ROTATING PHC POOL
              </span>
              <Watch size={20} style={{ color: "var(--accent-saffron)" }} />
            </div>

            <div
              className="metric-value"
              style={{
                fontSize: "clamp(30px, 3vw, 40px)",
                fontWeight: 900,
                color: "var(--accent-saffron)",
                lineHeight: 1.05,
              }}
            >
              ₹1,500
            </div>

            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>
              Loaned PHC Wristband
            </div>

            <p
              style={{
                margin: 0,
                fontSize: 13.5,
                lineHeight: 1.5,
                color: "var(--text-muted)",
              }}
            >
              Issued to <strong>high-risk mothers in their final 8 weeks</strong>{" "}
              of pregnancy, then sanitized and rotated to the next mother.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 12px",
              borderRadius: 10,
              background: isDark
                ? "rgba(245, 158, 11, 0.12)"
                : "rgba(245, 158, 11, 0.12)",
              fontSize: 12.5,
              fontWeight: 700,
              color: "var(--text)",
            }}
          >
            <motion.div
              animate={isActive ? { rotate: 360 } : {}}
              transition={{ repeat: Infinity, duration: 7, ease: "linear" }}
              style={{ display: "flex", color: "var(--accent-saffron)" }}
            >
              <RotateCw size={15} />
            </motion.div>
            <span>6+ mothers/year → &lt; ₹250 per delivery</span>
          </div>
        </motion.div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            color: "var(--accent-saffron)",
          }}
        >
          <ArrowRight size={20} />
        </div>

        {/* Stage 2: ₹0 Family Android Mode */}
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
            gap: 14,
            borderTop: "3px solid var(--accent-emerald)",
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
                  color: "var(--accent-emerald)",
                }}
              >
                UNIVERSAL ACCESS
              </span>
              <Smartphone size={20} style={{ color: "var(--accent-emerald)" }} />
            </div>

            <div
              className="metric-value"
              style={{
                fontSize: "clamp(30px, 3vw, 40px)",
                fontWeight: 900,
                color: "var(--accent-emerald)",
                lineHeight: 1.05,
              }}
            >
              ₹0
            </div>

            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>
              Family Android Mode
            </div>

            <p
              style={{
                margin: 0,
                fontSize: 13.5,
                lineHeight: 1.5,
                color: "var(--text-muted)",
              }}
            >
              Every other household uses the exact same signed offline APK on
              their existing Android phone for voice triage &amp; 2-tap SOS.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 12px",
              borderRadius: 10,
              background: isDark
                ? "rgba(16, 185, 129, 0.12)"
                : "rgba(16, 185, 129, 0.12)",
              fontSize: 12.5,
              fontWeight: 700,
              color: "var(--text)",
            }}
          >
            <CheckCircle2 size={15} style={{ color: "var(--accent-emerald)" }} />
            <span>Zero new hardware barrier for villages</span>
          </div>
        </motion.div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            color: "var(--accent-cyan)",
          }}
        >
          <ArrowRight size={20} />
        </div>

        {/* Stage 3: PHC Laptop -> ABDM / RCH Portal */}
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
            gap: 14,
            borderTop: "3px solid var(--accent-cyan)",
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
                  color: "var(--accent-cyan)",
                }}
              >
                NATIONAL INTEROP
              </span>
              <Building2 size={20} style={{ color: "var(--accent-cyan)" }} />
            </div>

            <div
              className="metric-value"
              style={{
                fontSize: "clamp(26px, 2.5vw, 34px)",
                fontWeight: 900,
                color: "var(--accent-cyan)",
                lineHeight: 1.12,
              }}
            >
              ABDM / RCH
            </div>

            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>
              PHC Laptop Gateway
            </div>

            <p
              style={{
                margin: 0,
                fontSize: 13.5,
                lineHeight: 1.5,
                color: "var(--text-muted)",
              }}
            >
              Runs 24×7 offline at the clinic; syncs cleanly to India&apos;s{" "}
              <strong>ABDM &amp; RCH Portal</strong> whenever town broadband is
              available.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 12px",
              borderRadius: 10,
              background: isDark
                ? "rgba(6, 182, 212, 0.12)"
                : "rgba(6, 182, 212, 0.12)",
              fontSize: 12.5,
              fontWeight: 700,
              color: "var(--text)",
            }}
          >
            <Globe size={15} style={{ color: "var(--accent-cyan)" }} />
            <span>Opportunistic sync · Zero vendor lock-in</span>
          </div>
        </motion.div>
      </div>

      {/* Bottom National Scale Summary Strip */}
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, y: 16 }}
        animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
        transition={{ delay: 0.52, duration: 0.45 }}
        style={{
          padding: "15px 22px",
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 14,
          textAlign: "center",
        }}
      >
        {[
          { k: "₹0 / mo", v: "Recurring Cloud Cost" },
          { k: "25,000+", v: "Target Indian PHCs" },
          { k: "100% Open", v: "NHM Budget Friendly" },
          { k: "ABHA Ready", v: "Clean RCH Sync Schema" },
        ].map((item) => (
          <div key={item.k}>
            <div
              style={{
                fontSize: 18,
                fontWeight: 800,
                color: "var(--text)",
              }}
            >
              {item.k}
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
              {item.v}
            </div>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
