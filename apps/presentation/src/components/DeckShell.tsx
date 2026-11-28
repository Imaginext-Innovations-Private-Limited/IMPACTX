import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  Grid,
  Maximize2,
  Minimize2,
  Moon,
  StickyNote,
  Sun,
  X,
} from "lucide-react";
import type { SlideMeta, ThemeMode } from "../types";
import { MeshCanvas } from "./MeshCanvas";

interface DeckShellProps {
  slides: SlideMeta[];
}

const THEME_STORAGE_KEY = "aarogya-deck-theme";

function getInitialSlideIndex(total: number): number {
  if (typeof window === "undefined") return 0;
  const match = window.location.hash.match(/slide-(\d+)/i);
  if (!match) return 0;
  const parsed = Number.parseInt(match[1], 10) - 1;
  if (Number.isNaN(parsed)) return 0;
  return Math.max(0, Math.min(total - 1, parsed));
}

function getInitialTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
  return saved === "light" ? "light" : "dark";
}

const slideVariants = {
  enter: (direction: number) => ({
    x: direction >= 0 ? 72 : -72,
    opacity: 0,
    scale: 0.965,
    filter: "blur(6px)",
  }),
  center: {
    x: 0,
    opacity: 1,
    scale: 1,
    filter: "blur(0px)",
  },
  exit: (direction: number) => ({
    x: direction >= 0 ? -72 : 72,
    opacity: 0,
    scale: 0.965,
    filter: "blur(6px)",
  }),
};

export const DeckShell: React.FC<DeckShellProps> = ({ slides }) => {
  const total = slides.length;
  const [currentIndex, setCurrentIndex] = useState<number>(() =>
    getInitialSlideIndex(total)
  );
  const [direction, setDirection] = useState<number>(1);
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [gridOpen, setGridOpen] = useState<boolean>(false);
  const [notesOpen, setNotesOpen] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const currentSlide = slides[currentIndex] ?? slides[0];

  // Sync theme attribute on <html> & localStorage
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // ignore storage errors in restricted environments
    }
  }, [theme]);

  // Sync URL hash for deep-linking & refresh persistence
  useEffect(() => {
    const desiredHash = `#slide-${currentIndex + 1}`;
    if (window.location.hash !== desiredHash) {
      window.history.replaceState(null, "", desiredHash);
    }
  }, [currentIndex]);

  // Listen to browser fullscreen changes
  useEffect(() => {
    const onFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  const goTo = useCallback(
    (targetIndex: number) => {
      const clamped = Math.max(0, Math.min(total - 1, targetIndex));
      if (clamped === currentIndex) return;
      setDirection(clamped > currentIndex ? 1 : -1);
      setCurrentIndex(clamped);
    },
    [currentIndex, total]
  );

  const goNext = useCallback(() => {
    goTo(currentIndex + 1);
  }, [currentIndex, goTo]);

  const goPrev = useCallback(() => {
    goTo(currentIndex - 1);
  }, [currentIndex, goTo]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const target = e.target as HTMLElement | null;
      const isEditable =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;
      if (isEditable) return;

      if (e.key === "Escape") {
        if (gridOpen) {
          setGridOpen(false);
          return;
        }
        if (notesOpen) {
          setNotesOpen(false);
          return;
        }
        return;
      }

      const lower = e.key.toLowerCase();
      if (lower === "t") {
        e.preventDefault();
        toggleTheme();
        return;
      }
      if (lower === "g") {
        e.preventDefault();
        setGridOpen((prev) => !prev);
        return;
      }
      if (lower === "n") {
        e.preventDefault();
        setNotesOpen((prev) => !prev);
        return;
      }
      if (lower === "f") {
        e.preventDefault();
        toggleFullscreen();
        return;
      }

      if (gridOpen) return;

      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        goNext();
      } else if (e.key === " ") {
        // Allow Space to click a focused button cleanly
        if (target?.tagName === "BUTTON" || target?.tagName === "A") return;
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "Home") {
        e.preventDefault();
        goTo(0);
      } else if (e.key === "End") {
        e.preventDefault();
        goTo(total - 1);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [goNext, goPrev, goTo, gridOpen, notesOpen, toggleFullscreen, toggleTheme, total]);

  // Touch swipe handlers
  const handleTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    if (gridOpen || e.touches.length !== 1) return;
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    if (!touchStartRef.current || gridOpen) return;
    const touch = e.changedTouches[0];
    const dx = touch.clientX - touchStartRef.current.x;
    const dy = touch.clientY - touchStartRef.current.y;
    touchStartRef.current = null;

    if (Math.abs(dx) > 52 && Math.abs(dx) > Math.abs(dy) * 1.4) {
      if (dx < 0) goNext();
      else goPrev();
    }
  };

  const ActiveSlideComponent = currentSlide.component;
  const formattedIndex = String(currentIndex + 1).padStart(2, "0");
  const formattedTotal = String(total).padStart(2, "0");
  const progressRatio = total > 0 ? (currentIndex + 1) / total : 0;

  return (
    <div
      className="deck-root"
      data-theme={theme}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Celestial / Daylight ambient aura + 60fps Mesh Canvas */}
      <div className="deck-aurora" aria-hidden="true" />
      <MeshCanvas theme={theme} />

      {/* Subtle top watermark */}
      <header className="deck-topbar">
        <button
          type="button"
          className="deck-brand-chip"
          onClick={() => goTo(0)}
          title="Jump to Slide 01 (Home)"
        >
          <span className="deck-brand-dot" />
          <span>Aarogya Mesh · आरोग्य संजाल</span>
        </button>
      </header>

      {/* Main animated slide stage */}
      <main className="deck-stage" aria-live="polite">
        <AnimatePresence mode="wait" custom={direction} initial={false}>
          <motion.section
            key={currentSlide.id}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              type: "spring",
              stiffness: 260,
              damping: 28,
              mass: 0.85,
            }}
            className="deck-slide-motion"
            aria-label={`Slide ${currentSlide.number}: ${currentSlide.title}`}
          >
            <ActiveSlideComponent theme={theme} isActive={true} />
          </motion.section>
        </AnimatePresence>
      </main>

      {/* Speaker Notes / Verbal Cues Drawer (N) */}
      <AnimatePresence>
        {notesOpen && (
          <motion.aside
            className="deck-notes-drawer"
            initial={{ opacity: 0, y: 18, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 14, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            aria-label="Speaker Notes"
          >
            <div className="deck-notes-head">
              <div>
                <div
                  style={{
                    fontSize: "0.72rem",
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "var(--accent-saffron)",
                  }}
                >
                  Speaker Cues · Slide {formattedIndex}
                </div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700 }}>
                  {currentSlide.title}
                </div>
              </div>
              <button
                type="button"
                className="hud-btn"
                onClick={() => setNotesOpen(false)}
                aria-label="Close speaker notes"
              >
                <X size={16} />
              </button>
            </div>
            <ul className="deck-notes-list">
              {currentSlide.speakerNotes.map((note, idx) => (
                <li key={idx} className="deck-notes-item">
                  {note}
                </li>
              ))}
            </ul>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Grid Overview Overlay (G) */}
      <AnimatePresence>
        {gridOpen && (
          <motion.div
            className="deck-grid-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            role="dialog"
            aria-modal="true"
            aria-label="Slide Grid Overview"
          >
            <div className="deck-grid-header">
              <div>
                <div
                  style={{
                    fontSize: "0.78rem",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "var(--accent-saffron)",
                  }}
                >
                  Deck Overview · 12 Slides
                </div>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 800 }}>
                  Aarogya Mesh — आरोग्य संजाल
                </h2>
              </div>
              <button
                type="button"
                className="pill"
                onClick={() => setGridOpen(false)}
                style={{ cursor: "pointer" }}
              >
                <X size={16} />
                <span>Close (Esc)</span>
              </button>
            </div>

            <div className="deck-grid-list">
              {slides.map((slide, idx) => {
                const isCurrent = idx === currentIndex;
                return (
                  <motion.button
                    key={slide.id}
                    type="button"
                    className={`deck-grid-card ${isCurrent ? "is-current" : ""}`}
                    onClick={() => {
                      goTo(idx);
                      setGridOpen(false);
                    }}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.025 }}
                  >
                    <span className="deck-grid-num">
                      SLIDE {String(slide.number).padStart(2, "0")}
                    </span>
                    <span className="deck-grid-title">{slide.title}</span>
                    <span className="deck-grid-sub">{slide.subtitle}</span>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sleek Floating Bottom HUD */}
      <nav className="deck-hud-wrap" aria-label="Presentation controls">
        <div className={`deck-hud ${notesOpen || gridOpen ? "is-active" : ""}`}>
          <button
            type="button"
            className="hud-btn"
            onClick={goPrev}
            disabled={currentIndex === 0}
            title="Previous slide (Left Arrow)"
            aria-label="Previous slide"
          >
            <ChevronLeft size={18} />
          </button>

          <span className="hud-counter" aria-label="Slide counter">
            {formattedIndex} / {formattedTotal}
          </span>

          <span className="hud-slide-title" title={currentSlide.title}>
            {currentSlide.title}
          </span>

          <button
            type="button"
            className="hud-btn"
            onClick={goNext}
            disabled={currentIndex === total - 1}
            title="Next slide (Right Arrow / Space)"
            aria-label="Next slide"
          >
            <ChevronRight size={18} />
          </button>

          <span className="hud-divider" aria-hidden="true" />

          <button
            type="button"
            className="hud-btn"
            onClick={toggleTheme}
            title="Toggle Dark / Light Theme (T)"
            aria-label="Toggle Dark or Light theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            <span className="hud-kbd">T</span>
          </button>

          <button
            type="button"
            className={`hud-btn ${gridOpen ? "is-on" : ""}`}
            onClick={() => setGridOpen((prev) => !prev)}
            title="Slide Grid Overview (G)"
            aria-label="Toggle slide grid overview"
          >
            <Grid size={16} />
            <span className="hud-kbd">G</span>
          </button>

          <button
            type="button"
            className={`hud-btn ${notesOpen ? "is-on" : ""}`}
            onClick={() => setNotesOpen((prev) => !prev)}
            title="Speaker Notes / Verbal Cues (N)"
            aria-label="Toggle speaker notes"
          >
            <StickyNote size={16} />
            <span className="hud-kbd">N</span>
          </button>

          <button
            type="button"
            className={`hud-btn ${isFullscreen ? "is-on" : ""}`}
            onClick={toggleFullscreen}
            title="Toggle Fullscreen (F)"
            aria-label="Toggle fullscreen"
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            <span className="hud-kbd">F</span>
          </button>
        </div>
      </nav>

      {/* Bottom edge progress bar */}
      <div className="deck-progress-track" aria-hidden="true">
        <motion.div
          className="deck-progress-fill"
          animate={{ scaleX: progressRatio }}
          transition={{ type: "spring", stiffness: 220, damping: 30 }}
        />
      </div>
    </div>
  );
};

export default DeckShell;
