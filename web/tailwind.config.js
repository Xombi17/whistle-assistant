/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "oklch(13.2% 0.022 258)",
        "paper-2": "oklch(16.4% 0.02 258)",
        "paper-3": "oklch(20% 0.02 258)",
        ink: "oklch(93.5% 0.012 85)",
        "ink-2": "oklch(80% 0.015 255)",
        muted: "oklch(65% 0.02 255)",
        rule: "oklch(27% 0.02 258)",
        "rule-2": "oklch(22% 0.015 258)",
        accent: "oklch(75% 0.12 185)",
        "accent-soft": "oklch(24% 0.04 185)",
        signal: "oklch(82% 0.095 68)",
      },
      fontFamily: {
        display: ['"Instrument Sans"', 'system-ui', 'sans-serif'],
        body: ['"Figtree"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'monospace'],
        sans: ['"Figtree"', 'system-ui', 'sans-serif']
      }
    },
  },
  plugins: [],
}
