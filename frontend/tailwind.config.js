/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'fantasy-burgundy': '#3c0f0f',
        'fantasy-gold': '#d4b36b',
        'fantasy-parchment': '#e7d8b1',
        'fantasy-dark': '#1a0a0a',
        'fantasy-red': '#6b1a1a',
      },
      boxShadow: {
        'gold-glow': '0 0 20px rgba(212, 179, 107, 0.3)',
        'gold-glow-strong': '0 0 30px rgba(212, 179, 107, 0.6)',
      },
      backgroundImage: {
        'parchment': "url('data:image/svg+xml,%3Csvg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"%3E%3Cfilter id=\"noise\"%3E%3CfeTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"4\" /%3E%3C/filter%3E%3Crect width=\"100\" height=\"100\" filter=\"url(%23noise)\" opacity=\"0.05\"/%3E%3C/svg%3E')",
      },
    },
  },
  plugins: [],
}

