/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        foreground: '#f8fafc',
        card: 'rgba(15, 23, 42, 0.6)',
        'card-border': 'rgba(51, 65, 85, 0.5)',
        brand: {
          purple: '#8B5CF6',
          cyan: '#06B6D4',
          emerald: '#10B981',
          royal: '#3B82F6',
        }
      }
    },
  },
  plugins: [],
}
