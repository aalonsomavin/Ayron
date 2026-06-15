/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../backend/templates/**/*.html",
    "../backend/apps/**/templates/**/*.html",
    "./src/**/*.css",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["Geist Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
