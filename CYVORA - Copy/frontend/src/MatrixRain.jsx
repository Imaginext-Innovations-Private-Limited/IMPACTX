
import { useEffect, useRef } from "react";

export default function MatrixRain() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    let animationId;
    let width = 0;
    let height = 0;
    let frame = 0;
    let columns = [];

    const fontSize = 17;
    const characters = "01";

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);

      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const count = Math.ceil(width / fontSize);

      columns = Array.from({ length: count }, () => {
        const length = 10 + Math.floor(Math.random() * 15);

        return {
          y: Math.random() * height,
          speed: 0.20 + Math.random() * 0.25,
          length,
          digits: Array.from(
            { length },
            () => characters[Math.floor(Math.random() * 2)]
          ),
        };
      });
    };

    const draw = () => {
      frame++;

      ctx.fillStyle = "rgba(2, 8, 18, 0.10)";
      ctx.fillRect(0, 0, width, height);

      ctx.font = "bold 18px monospace";
ctx.textBaseline = "top";
ctx.shadowColor = "#00bfff";
ctx.shadowBlur = 5;

      columns.forEach((column, index) => {
        const x = index * fontSize;

        // Change digits only once every 90 frames
        if (frame % 90 === 0) {
          const position = Math.floor(
            Math.random() * column.length
          );

          column.digits[position] =
            characters[Math.floor(Math.random() * 2)];
        }

        for (let i = 0; i < column.length; i++) {
          const y = column.y - i * fontSize;

          if (y < 0 || y > height) continue;

          const opacity = Math.max(
            0.45,
            1 - (i / column.length) * 0.45
          );

          ctx.fillStyle =
            i === 0
              ? `rgba(110, 225, 255, ${opacity})`
              : `rgba(35, 160, 230, ${opacity})`;

          ctx.fillText(column.digits[i], x, y);
        }

        // Slow falling movement
        column.y += column.speed;

        if (column.y - column.length * fontSize > height) {
          column.y = -Math.random() * height * 0.3;
          column.speed = 0.20 + Math.random() * 0.25;
        }
      });ctx.shadowBlur = 0;

      animationId = requestAnimationFrame(draw);
    };

    resize();
    draw();

    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="matrix-rain"
      aria-hidden="true"
    />
  );
}
