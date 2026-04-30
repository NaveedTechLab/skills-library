/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',  // required — enables dark: variants via <html class="dark">
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      screens: {
        'xl': '1440px',  // wide desktop — override default 1280px
      },
      colors: {
        gray: {
          750: '#2d3748',  // between 700 (#374151) and 800 (#1f2937) for hover states
          950: '#0a0f1e',  // deep dark page background
        },
      },
    },
  },
  plugins: [],
};
