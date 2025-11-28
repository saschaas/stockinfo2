/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm background colors
        cream: {
          DEFAULT: '#FDF8F3',
          dark: '#FAF5EF',
          darker: '#F5EDE4',
        },
        // Primary accent - Teal
        primary: {
          50: '#F0F9F7',
          100: '#D1F0E9',
          200: '#A3E1D4',
          300: '#75D1BE',
          400: '#47C2A9',
          500: '#2A9D8F',
          600: '#238577',
          700: '#1C6D5F',
          800: '#155447',
          900: '#0E3C2F',
        },
        // Warm border colors
        border: {
          warm: '#E8E0D8',
          'warm-dark': '#D4C8BC',
        },
        // Semantic colors - softer versions
        success: {
          50: '#E8F5E9',
          100: '#C8E6C9',
          500: '#4CAF50',
          600: '#43A047',
          700: '#2E7D32',
        },
        warning: {
          50: '#FFF8E1',
          100: '#FFECB3',
          500: '#FFB300',
          600: '#FFA000',
          700: '#FF8F00',
        },
        danger: {
          50: '#FFEBEE',
          100: '#FFCDD2',
          500: '#E57373',
          600: '#EF5350',
          700: '#D32F2F',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      borderRadius: {
        'card': '1.25rem',   // 20px - generous card rounding
        '2xl': '1rem',       // 16px
        '3xl': '1.5rem',     // 24px
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.04), 0 4px 24px rgba(0, 0, 0, 0.02)',
        'card-hover': '0 4px 12px rgba(0, 0, 0, 0.06), 0 8px 32px rgba(0, 0, 0, 0.04)',
        'elevated': '0 4px 12px rgba(0, 0, 0, 0.08), 0 8px 32px rgba(0, 0, 0, 0.04)',
        'soft': '0 1px 3px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.02)',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '112': '28rem',
        '128': '32rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
