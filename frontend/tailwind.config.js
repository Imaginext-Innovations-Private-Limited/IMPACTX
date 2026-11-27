/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        farm: {
          green: '#16a34a',
          'green-light': '#22c55e',
          'green-dark': '#14532d',
          earth: '#92400e',
          gold: '#d97706',
          sky: '#0ea5e9',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
