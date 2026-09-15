/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'cyber-cyan': '#00f0ff',
        'cyber-magenta': '#ff2a6d',
        'cyber-green': '#05ffa1',
        'cyber-chrome': {
          200: '#d1d4de',
          300: '#b2b7c7',
          400: '#939ab0',
          500: '#747d99',
        },
        'app-bg': '#050608',
        'app-panel': '#0a0b12',
        'app-subpanel': '#111320',
        'app-border': '#1e2238',
      },
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        header: ['Rajdhani', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        body: ['Exo 2', 'sans-serif'],
      },
      boxShadow: {
        'glow-cyan': '0 0 12px rgba(0, 240, 255, 0.4)',
        'glow-magenta': '0 0 12px rgba(255, 42, 109, 0.4)',
        'glow-green': '0 0 12px rgba(5, 255, 161, 0.4)',
        'panel': '0 8px 32px rgba(0, 0, 0, 0.45)',
      },
    },
  },
  plugins: [],
}
