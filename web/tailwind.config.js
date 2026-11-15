/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        chassis: "#070a12",
        panel: "#0e1422",
        panelBorder: "#1b253b",
        neonCyan: "#00d2ff",
        neonBlue: "#3b82f6",
        neonEmerald: "#10b981",
        neonRose: "#f43f5e"
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif']
      }
    },
  },
  plugins: [],
}
