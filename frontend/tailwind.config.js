/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        maravilha: {
          blue: '#4E7A9C',
          'blue-light': '#6899BA',
          'blue-dark': '#3F6785',
          dark: '#1F3347',
          'dark-card': '#1B3B54',
          gold: '#EAA43B',
          'gold-hover': '#DF982D',
          border: '#E2E8F0',
          bg: '#F8FAFC',
          muted: '#64748B'
        },
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        navy: {
          800: '#0f172a',
          900: '#0b1120',
          950: '#020617',
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
        serif: ['Playfair Display', 'Cormorant Garamond', 'Georgia', 'serif'],
        display: ['Playfair Display', 'serif'],
      },
      letterSpacing: {
        widest2: '.25em',
        widest3: '.35em',
      }
    },
  },
  plugins: [],
}
