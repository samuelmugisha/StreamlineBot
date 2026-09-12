/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: 'var(--brand-primary)',
          light:   'var(--brand-light)',
          accent:  'var(--brand-accent)',
        },
      },
    },
  },
  plugins: [],
}
