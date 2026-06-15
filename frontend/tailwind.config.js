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
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["lofi", "black"],
  },
};
