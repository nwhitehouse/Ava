/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme')

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // Include all JS/TS/JSX/TSX files in src
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Jura', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        'user-message-bg': '#F3F4FC',
      },
    },
  },
  plugins: [],
} 