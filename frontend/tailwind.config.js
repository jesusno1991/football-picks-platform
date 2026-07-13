/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0f172a',
        panel: '#ffffff',
        line: '#e2e8f0',
        brand: '#0891b2'
      }
    },
  },
  plugins: [],
}
