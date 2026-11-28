import React, { useEffect, useRef } from "react";
import type { ThemeMode } from "../types";

interface MeshCanvasProps {
  theme: ThemeMode;
}

interface MeshNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  colorIndex: number;
  phase: number;
}

interface DataPulse {
  from: number;
  to: number;
  t: number;
  speed: number;
  colorIndex: number;
}

const DARK_PALETTE = [
  "245, 158, 11", // saffron
  "16, 185, 129", // emerald
  "6, 182, 212",  // cyan
];

const LIGHT_PALETTE = [
  "217, 119, 6",  // deep saffron
  "5, 150, 105",  // deep emerald
  "2, 132, 199",  // deep cyan
];

export const MeshCanvas: React.FC<MeshCanvasProps> = ({ theme }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const themeRef = useRef<ThemeMode>(theme);

  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    let width = window.innerWidth;
    let height = window.innerHeight;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();

    const nodeCount = Math.max(26, Math.min(48, Math.floor((width * height) / 34000)));
    const nodes: MeshNode[] = Array.from({ length: nodeCount }, (_, i) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.28,
      vy: (Math.random() - 0.5) * 0.28,
      radius: 1.8 + Math.random() * 2.1,
      colorIndex: i % 3,
      phase: Math.random() * Math.PI * 2,
    }));

    const pulses: DataPulse[] = [];
    const maxLinkDist = 175;
    let frameId = 0;
    let lastTime = performance.now();
    let pulseCooldown = 0.6;

    const renderFrame = (now: number) => {
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      const isDark = themeRef.current === "dark";
      const palette = isDark ? DARK_PALETTE : LIGHT_PALETTE;
      const edgeBaseAlpha = isDark ? 0.22 : 0.16;
      const nodeCoreAlpha = isDark ? 0.78 : 0.62;
      const haloAlpha = isDark ? 0.24 : 0.15;

      ctx.clearRect(0, 0, width, height);

      // Update node positions gently
      if (!reducedMotion) {
        for (const n of nodes) {
          n.x += n.vx * (dt * 60);
          n.y += n.vy * (dt * 60);
          n.phase += dt * 1.4;

          if (n.x < -20) n.x = width + 20;
          if (n.x > width + 20) n.x = -20;
          if (n.y < -20) n.y = height + 20;
          if (n.y > height + 20) n.y = -20;
        }
      }

      // Draw connecting mesh edges and collect nearby pairs for pulses
      const candidatePairs: Array<[number, number]> = [];
      ctx.lineWidth = 1;

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < maxLinkDist * maxLinkDist) {
            const dist = Math.sqrt(distSq);
            const strength = 1 - dist / maxLinkDist;
            const alpha = strength * strength * edgeBaseAlpha;
            const rgb = palette[a.colorIndex];
            ctx.strokeStyle = `rgba(${rgb}, ${alpha.toFixed(3)})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();

            if (strength > 0.25 && candidatePairs.length < 40) {
              candidatePairs.push([i, j]);
            }
          }
        }
      }

      // Spawn & animate glowing data-pulse packets along active mesh edges
      if (!reducedMotion) {
        pulseCooldown -= dt;
        if (pulseCooldown <= 0 && candidatePairs.length > 0 && pulses.length < 7) {
          const [aIdx, bIdx] =
            candidatePairs[Math.floor(Math.random() * candidatePairs.length)];
          const reverse = Math.random() > 0.5;
          pulses.push({
            from: reverse ? bIdx : aIdx,
            to: reverse ? aIdx : bIdx,
            t: 0,
            speed: 0.48 + Math.random() * 0.42,
            colorIndex: Math.floor(Math.random() * 3),
          });
          pulseCooldown = 0.55 + Math.random() * 0.9;
        }

        for (let i = pulses.length - 1; i >= 0; i--) {
          const p = pulses[i];
          p.t += dt * p.speed;
          if (p.t >= 1) {
            pulses.splice(i, 1);
            continue;
          }
          const a = nodes[p.from];
          const b = nodes[p.to];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          if (dx * dx + dy * dy > (maxLinkDist + 40) * (maxLinkDist + 40)) {
            pulses.splice(i, 1);
            continue;
          }

          const px = a.x + dx * p.t;
          const py = a.y + dy * p.t;
          const rgb = palette[p.colorIndex];
          const fade = Math.sin(p.t * Math.PI);

          const grad = ctx.createRadialGradient(px, py, 0, px, py, 10);
          grad.addColorStop(0, `rgba(${rgb}, ${(0.85 * fade).toFixed(3)})`);
          grad.addColorStop(0.45, `rgba(${rgb}, ${(0.3 * fade).toFixed(3)})`);
          grad.addColorStop(1, `rgba(${rgb}, 0)`);
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(px, py, 10, 0, Math.PI * 2);
          ctx.fill();

          ctx.fillStyle = `rgba(255, 255, 255, ${(0.9 * fade).toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(px, py, 2.1, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Draw luminous mesh nodes
      for (const n of nodes) {
        const rgb = palette[n.colorIndex];
        const breathe = 0.85 + 0.25 * Math.sin(n.phase);
        const haloR = n.radius * 4.4 * breathe;

        const halo = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, haloR);
        halo.addColorStop(0, `rgba(${rgb}, ${(haloAlpha * breathe).toFixed(3)})`);
        halo.addColorStop(1, `rgba(${rgb}, 0)`);
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(n.x, n.y, haloR, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = `rgba(${rgb}, ${nodeCoreAlpha})`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      if (!reducedMotion) {
        frameId = window.requestAnimationFrame(renderFrame);
      }
    };

    frameId = window.requestAnimationFrame(renderFrame);
    window.addEventListener("resize", resize);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="deck-canvas" aria-hidden="true" />;
};

export default MeshCanvas;
