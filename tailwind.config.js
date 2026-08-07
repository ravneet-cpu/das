/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gallery: {
          black: '#0a0a0a',
          charcoal: '#1a1a1a',
          'dark-gray': '#2a2a2a',
          'medium-gray': '#4a4a4a',
          'light-gray': '#8a8a8a',
          'off-white': '#f8f8f8',
          'pure-white': '#ffffff',
          accent: '#c9a961',
        }
      },
      fontFamily: {
        'display': ['Playfair Display', 'serif'],
        'body': ['Inter', 'sans-serif'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      boxShadow: {
        'gallery': '0 20px 40px rgba(0, 0, 0, 0.8)',
        'gallery-hover': '0 15px 40px rgba(0, 0, 0, 0.9), 0 8px 16px rgba(0, 0, 0, 0.7)',
        'gallery-frame': '0 0 0 1px #2a2a2a, 0 10px 30px rgba(0, 0, 0, 0.8), 0 4px 8px rgba(0, 0, 0, 0.6)',
      },
      animation: {
        'gallery-loading': 'gallery-loading 2s infinite',
      },
      keyframes: {
        'gallery-loading': {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        }
      }
    },
  },
  plugins: [],
}
