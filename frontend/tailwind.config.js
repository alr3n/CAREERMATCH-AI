import containerQueries from "@tailwindcss/container-queries";
import plugin from "tailwindcss/plugin";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F7F5",
        surface: "#FFFFFF",
        ink: "#17212B",
        muted: "#5A6672",
        line: "#DCE1DE",
        teal: { DEFAULT: "#0F6E66", dark: "#0A524C", tint: "#E2F0EC", soft: "#A9D3CB" },
        amber: { DEFAULT: "#9A4A0B", tint: "#FBF0E3" },
        danger: { DEFAULT: "#A61B1B", tint: "#FCEBEB" },
        // Score-ledger component colours (sequential teal → slate, colour-blind safe ordering)
        ledger: {
          semantic: "#0F6E66",
          required: "#2E8C80",
          preferred: "#6BB3A6",
          experience: "#3D5A80",
          preference: "#7A93B5",
          relevance: "#B7C6D9",
        },
      },
      fontFamily: {
        sans: ['"Schibsted Grotesk Variable"', "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      fontSize: {
        // Modular scale (≈1.25) anchored at 16px body text
        xs: ["0.8rem", { lineHeight: "1.15rem" }],
        sm: ["0.9rem", { lineHeight: "1.35rem" }],
        base: ["1rem", { lineHeight: "1.6rem" }],
        lg: ["1.25rem", { lineHeight: "1.8rem" }],
        xl: ["1.563rem", { lineHeight: "2.1rem" }],
        "2xl": ["1.953rem", { lineHeight: "2.4rem" }],
        "3xl": ["2.441rem", { lineHeight: "2.8rem" }],
        "4xl": ["3.052rem", { lineHeight: "3.3rem" }],
      },
      maxWidth: { prose: "68ch" },
      borderRadius: { sm: "4px", DEFAULT: "6px", lg: "10px" },
    },
  },
  plugins: [
    // Size components by the space they actually get (job cards sit in columns of very different widths).
    containerQueries,
    // Larger touch targets only where the primary pointer is a finger (phones, tablets).
    plugin(({ addVariant }) => addVariant("pointer-coarse", "@media (pointer: coarse)")),
  ],
};
