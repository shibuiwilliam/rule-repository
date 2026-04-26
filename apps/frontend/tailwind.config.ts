import type { Config } from "tailwindcss";

/**
 * Design tokens for the Rule Repository frontend.
 * Centralizes colors, spacing, and typography per CLAUDE.md §6.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Rule modality colors
        modality: {
          must: { bg: "#fee2e2", text: "#991b1b" },
          "must-not": { bg: "#fecaca", text: "#7f1d1d" },
          should: { bg: "#fef9c3", text: "#854d0e" },
          may: { bg: "#dcfce7", text: "#166534" },
          info: { bg: "#dbeafe", text: "#1e40af" },
        },
        // Rule severity colors
        severity: {
          critical: "#dc2626",
          high: "#f97316",
          medium: "#eab308",
          low: "#9ca3af",
        },
        // Verdict colors
        verdict: {
          allow: "#22c55e",
          deny: "#ef4444",
          confirm: "#f59e0b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
