/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0e27',
          800: '#10143d',
          700: '#1a1f4b',
          600: '#242b59',
        }
      }
    },
  },
  plugins: [],
}
