/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: {
          900: "#09090b",
          800: "#0f1014",
          700: "#16181d",
          600: "#1f2229",
        },
        accent: {
          DEFAULT: "#3b82f6",
          400: "#60a5fa",
          500: "#2563eb",
          600: "#1d4ed8",
        },
      },
      fontFamily: {
        sans: [
          "InterVariable",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 2px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.04)",
      },
    },
  },
  plugins: [],
};
