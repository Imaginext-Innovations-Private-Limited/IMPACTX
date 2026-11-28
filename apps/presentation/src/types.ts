import type React from "react";

export type ThemeMode = "dark" | "light";

export interface SlideProps {
  theme: ThemeMode;
  isActive: boolean;
}

export interface SlideMeta {
  id: string;
  number: number;
  title: string;
  subtitle: string;
  speakerNotes: string[];
  component: React.ComponentType<SlideProps>;
}
