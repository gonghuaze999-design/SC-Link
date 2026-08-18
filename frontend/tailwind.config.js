/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#2563EB', 600: '#2563EB', 700: '#1D4ED8' },
        navy: '#0F172A',
        ink: '#1E293B',
        muted: '#64748B',
        line: '#E2E8F0',
        cyan2: '#06B6D4',
      },
    },
  },
  plugins: [],
}
